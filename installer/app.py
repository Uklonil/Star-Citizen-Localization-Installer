from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

try:
    import flet_desktop.version  # noqa: F401
except ModuleNotFoundError:
    pass

try:
    from .installer_core import (
        DEFAULT_VARIANT,
        VARIANT_LABELS,
        detect_install_paths,
        discover_asset_bundle,
        install_variant,
        is_running_as_admin,
        normalize_install_path,
        path_requires_admin,
    )
except ImportError:
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    for candidate in (current_dir, parent_dir):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
    try:
        from installer.installer_core import (
            DEFAULT_VARIANT,
            VARIANT_LABELS,
            detect_install_paths,
            discover_asset_bundle,
            install_variant,
            is_running_as_admin,
            normalize_install_path,
            path_requires_admin,
        )
    except ImportError:
        from installer_core import (
            DEFAULT_VARIANT,
            VARIANT_LABELS,
            detect_install_paths,
            discover_asset_bundle,
            install_variant,
            is_running_as_admin,
            normalize_install_path,
            path_requires_admin,
        )


VARIANT_DESCRIPTIONS = {
    "base": "Instala solo la traduccion base.",
    "componentes": "Anade los nombres extendidos de componentes sobre la traduccion base.",
    "blueprints": "Anade las marcas [BP] y los ajustes de blueprint sobre la traduccion base.",
    "componentes-blueprints": "Instala la traduccion base con ambos overlays activos.",
}


def main(page: ft.Page) -> None:
    bundle = discover_asset_bundle()
    page.title = "Star Citizen Spanish Installer"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 24
    page.window.width = 920
    page.window.height = 760
    page.window.resizable = False
    page.window.maximizable = False
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.ORANGE)
    page.bgcolor = "#111315"
    page.scroll = ft.ScrollMode.AUTO

    available_variants = [name for name in VARIANT_LABELS if name in bundle.variants]
    default_variant = DEFAULT_VARIANT if DEFAULT_VARIANT in bundle.variants else available_variants[0]

    status_text = ft.Text(
        value=f"Paquete detectado: {bundle.version}",
        size=13,
        color="#C7CDD3",
    )
    permission_text = ft.Text(size=12, color="#AAB3BB")
    progress_ring = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)
    path_field = ft.TextField(
        label="Ruta de instalacion",
        hint_text=r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE",
        expand=True,
        autofocus=True,
    )
    variant_group = ft.RadioGroup(
        content=ft.Column(spacing=10),
        value=default_variant,
    )
    install_button = ft.FilledButton(
        text="Instalar o sobrescribir",
        icon=ft.Icons.DOWNLOAD_DONE,
    )
    confirm_dialog: ft.AlertDialog | None = None
    result_dialog: ft.AlertDialog | None = None

    def set_busy(is_busy: bool, message: str | None = None) -> None:
        install_button.disabled = is_busy
        progress_ring.visible = is_busy
        if message is not None:
            update_status(message)
        page.update()

    def update_status(message: str, *, error: bool = False) -> None:
        status_text.value = message
        status_text.color = "#FFB4AB" if error else "#C7CDD3"
        page.update()

    def show_snackbar(message: str, *, error: bool = False) -> None:
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor="#7F1D1D" if error else "#24323E",
        )
        page.open(page.snack_bar)

    def set_install_path(path: str | Path) -> None:
        normalized = normalize_install_path(path)
        path_field.value = str(normalized)
        admin_required = path_requires_admin(normalized)
        if admin_required and not is_running_as_admin():
            permission_text.value = "La ruta seleccionada esta en Program Files. Necesitas ejecutar el instalador como administrador."
            permission_text.color = "#FFB4AB"
        elif admin_required:
            permission_text.value = "El instalador tiene privilegios de administrador para escribir en Program Files."
            permission_text.color = "#A9D18E"
        else:
            permission_text.value = "La ruta seleccionada no requiere permisos elevados."
            permission_text.color = "#AAB3BB"
        page.update()

    def autodetect_install_path(_: ft.ControlEvent | None = None) -> None:
        candidates = detect_install_paths()
        if candidates:
            set_install_path(candidates[0])
            update_status(f"Ruta detectada automaticamente: {candidates[0]} | Paquete: {bundle.version}")
            return
        update_status(
            f"No se ha detectado la instalacion automaticamente. Selecciona una ruta manual. | Paquete: {bundle.version}",
            error=True,
        )

    def handle_directory_result(event: ft.FilePickerResultEvent) -> None:
        if event.path:
            set_install_path(event.path)
            update_status(f"Ruta seleccionada manualmente: {path_field.value} | Paquete: {bundle.version}")

    file_picker = ft.FilePicker(on_result=handle_directory_result)
    page.overlay.append(file_picker)

    def browse_install_path(_: ft.ControlEvent) -> None:
        file_picker.get_directory_path(dialog_title="Selecciona la carpeta LIVE o la carpeta StarCitizen")

    def confirm_install(_: ft.ControlEvent) -> None:
        raw_path = (path_field.value or "").strip()
        if not raw_path:
            show_snackbar("Indica una ruta de instalacion.", error=True)
            return

        variant_name = variant_group.value
        variant_dir = bundle.variants.get(variant_name)
        if variant_dir is None:
            show_snackbar("La variante seleccionada no esta disponible.", error=True)
            return

        try:
            install_root = normalize_install_path(raw_path)
        except Exception as exc:
            show_snackbar(f"Ruta no valida: {exc}", error=True)
            return

        def close_dialog(_: ft.ControlEvent | None = None) -> None:
            if confirm_dialog is not None:
                page.close(confirm_dialog)
            if result_dialog is not None:
                page.close(result_dialog)

        def execute_install(_: ft.ControlEvent) -> None:
            if confirm_dialog is not None:
                page.close(confirm_dialog)
            set_busy(True, f"Instalando {VARIANT_LABELS[variant_name]} en {install_root}...")

            try:
                copied_files = install_variant(variant_dir=variant_dir, install_root=install_root)
            except Exception as exc:
                update_status(f"Error de instalacion: {exc}", error=True)
                show_snackbar(str(exc), error=True)
                set_busy(False)
                return

            set_busy(False)
            update_status(
                f"Instalacion completada en {install_root} | Variante: {variant_name} | Archivos: {len(copied_files)}"
            )
            copied_preview = "\n".join(str(path) for path in copied_files[:6])
            if len(copied_files) > 6:
                copied_preview += f"\n... y {len(copied_files) - 6} mas"

            nonlocal result_dialog
            result_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Instalacion completada"),
                content=ft.Text(
                    "\n".join(
                        [
                            f"Version del paquete: {bundle.version}",
                            f"Destino: {install_root}",
                            f"Variante: {VARIANT_LABELS[variant_name]}",
                            f"Archivos copiados: {len(copied_files)}",
                            "",
                            copied_preview,
                        ]
                    )
                ),
                actions=[ft.TextButton("Cerrar", on_click=close_dialog)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(result_dialog)

        nonlocal confirm_dialog
        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar instalacion"),
            content=ft.Text(
                "\n".join(
                    [
                        f"Se copiaran los archivos de '{VARIANT_LABELS[variant_name]}' en:",
                        "",
                        str(install_root),
                        "",
                        "Los archivos existentes se sobrescribiran si ya estan presentes.",
                    ]
                )
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dialog),
                ft.FilledButton("Instalar", on_click=execute_install),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        show_snackbar("Preparando instalacion...")
        page.open(confirm_dialog)

    install_button.on_click = confirm_install

    variant_cards = []
    for variant_name in available_variants:
        variant_cards.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Radio(value=variant_name),
                        ft.Column(
                            controls=[
                                ft.Text(VARIANT_LABELS[variant_name], weight=ft.FontWeight.W_600, size=15),
                                ft.Text(
                                    VARIANT_DESCRIPTIONS[variant_name],
                                    size=12,
                                    color="#B8C0C7",
                                ),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                border=ft.border.all(1, "#2C3138"),
                border_radius=12,
                padding=14,
                bgcolor="#171B20",
            )
        )

    variant_group.content.controls = variant_cards

    page.add(
        ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Instalador de traduccion al espanol para Star Citizen",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        "Detecta la carpeta del juego, permite elegir la combinacion de overlays y copia los archivos sobre la instalacion existente.",
                        size=14,
                        color="#C7CDD3",
                    ),
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Instalacion", size=18, weight=ft.FontWeight.W_600),
                                ft.Row(
                                    controls=[
                                        path_field,
                                        ft.OutlinedButton("Examinar", icon=ft.Icons.FOLDER_OPEN, on_click=browse_install_path),
                                    ],
                                ),
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            "Acepta la carpeta LIVE directamente o la raiz de StarCitizen si contiene LIVE/EPTU/PTU.",
                                            size=12,
                                            color="#AAB3BB",
                                            expand=True,
                                        ),
                                        ft.TextButton("Autodetectar", icon=ft.Icons.MY_LOCATION, on_click=autodetect_install_path),
                                    ],
                                ),
                                permission_text,
                            ],
                            spacing=10,
                        ),
                        padding=18,
                        border_radius=16,
                        bgcolor="#171B20",
                    ),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Contenido a instalar", size=18, weight=ft.FontWeight.W_600),
                                variant_group,
                            ],
                            spacing=12,
                        ),
                        padding=18,
                        border_radius=16,
                        bgcolor="#171B20",
                    ),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Estado", size=18, weight=ft.FontWeight.W_600),
                                status_text,
                            ],
                            spacing=8,
                        ),
                        padding=18,
                        border_radius=16,
                        bgcolor="#171B20",
                    ),
                    ft.Row(
                        controls=[
                            install_button,
                            progress_ring,
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=18,
            ),
            width=840,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#16191C", "#0F1214"],
            ),
            padding=4,
        )
    )

    autodetect_install_path()


if __name__ == "__main__":
    ft.app(target=main)
