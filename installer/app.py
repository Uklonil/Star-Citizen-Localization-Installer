from __future__ import annotations

import json
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
        LanguageBundle,
        VARIANT_IDS,
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
            VARIANT_IDS,
            detect_install_paths,
            discover_asset_bundle,
            LanguageBundle,
            install_variant,
            is_running_as_admin,
            normalize_install_path,
            path_requires_admin,
        )
    except ImportError:
        from installer_core import (
            DEFAULT_VARIANT,
            VARIANT_IDS,
            detect_install_paths,
            discover_asset_bundle,
            LanguageBundle,
            install_variant,
            is_running_as_admin,
            normalize_install_path,
            path_requires_admin,
        )

DEFAULT_UI_LANGUAGE = "en"
_UI_CACHE: dict[str, dict[str, str]] = {}
KO_FI_URL = "https://ko-fi.com/uklonil"


def _app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _ui_texts_dir() -> Path:
    return _app_base_dir() / "installer" / "ui_texts"


def _assets_dir() -> Path:
    return _app_base_dir() / "installer" / "assets"


def _load_ui_text_file(language_code: str) -> dict[str, str]:
    cached = _UI_CACHE.get(language_code)
    if cached is not None:
        return cached

    ui_file = _ui_texts_dir() / f"{language_code}.json"
    if not ui_file.is_file():
        _UI_CACHE[language_code] = {}
        return _UI_CACHE[language_code]

    data = json.loads(ui_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"El fichero de UI no contiene un objeto JSON valido: {ui_file}")

    normalized = {str(key): str(value) for key, value in data.items()}
    _UI_CACHE[language_code] = normalized
    return normalized


def load_ui_strings(language_code: str) -> dict[str, str]:
    english_strings = _load_ui_text_file(DEFAULT_UI_LANGUAGE)
    if not english_strings:
        raise FileNotFoundError("No se ha encontrado la base de textos de UI en ingles.")

    if language_code == DEFAULT_UI_LANGUAGE:
        return english_strings

    localized_strings = _load_ui_text_file(language_code)
    merged = dict(english_strings)
    merged.update(localized_strings)
    return merged


def main(page: ft.Page) -> None:
    bundle = discover_asset_bundle()
    window_icon = _assets_dir() / "app-icon.ico"
    if window_icon.is_file():
        page.window.icon = str(window_icon)
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 24
    page.window.width = 920
    page.window.height = 760
    page.window.resizable = False
    page.window.maximizable = False
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.PURPLE)
    page.bgcolor = "#111315"
    page.scroll = ft.ScrollMode.AUTO

    available_languages = list(bundle.languages.values())
    default_language = next((language for language in available_languages if language.code == "en"), available_languages[0])
    selected_language: LanguageBundle = default_language
    available_variants = [name for name in VARIANT_IDS if name in selected_language.variants]
    default_variant = DEFAULT_VARIANT if DEFAULT_VARIANT in selected_language.variants else available_variants[0]

    def strings() -> dict[str, str]:
        return load_ui_strings(selected_language.code)

    status_text = ft.Text(
        value="",
        size=13,
        color="#C7CDD3",
    )
    permission_text = ft.Text(size=12, color="#AAB3BB")
    progress_ring = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)
    path_field = ft.TextField(
        label="",
        hint_text="",
        expand=True,
        autofocus=True,
    )
    headline_text = ft.Text(size=28, weight=ft.FontWeight.BOLD)
    subheadline_text = ft.Text(size=14, color="#C7CDD3")
    install_section_text = ft.Text(size=18, weight=ft.FontWeight.W_600)
    path_help_text = ft.Text(size=12, color="#AAB3BB", expand=True)
    content_section_text = ft.Text(size=18, weight=ft.FontWeight.W_600)
    status_section_text = ft.Text(size=18, weight=ft.FontWeight.W_600)
    footer_text = ft.Text(size=12, color="#8E98A1")
    language_dropdown = ft.Dropdown(
        label="",
        value=default_language.code,
        options=[ft.dropdown.Option(language.code, language.label) for language in available_languages],
        width=260,
    )
    variant_group = ft.RadioGroup(
        content=ft.Column(spacing=10),
        value=default_variant,
    )
    install_button = ft.FilledButton(
        text="",
        icon=ft.Icons.DOWNLOAD_DONE,
    )
    browse_button = ft.OutlinedButton("", icon=ft.Icons.FOLDER_OPEN)
    autodetect_button = ft.TextButton("", icon=ft.Icons.MY_LOCATION)
    kofi_button = ft.TextButton(icon=ft.Icons.OPEN_IN_NEW)
    confirm_dialog: ft.AlertDialog | None = None
    result_dialog: ft.AlertDialog | None = None

    def format_text(key: str, **kwargs: object) -> str:
        return strings()[key].format(**kwargs)

    def variant_label(variant_name: str) -> str:
        return strings()[f"variant_{variant_name.replace('-', '_')}_label"]

    def variant_description(variant_name: str) -> str:
        return strings()[f"variant_{variant_name.replace('-', '_')}_desc"]

    def apply_ui_language() -> None:
        page.title = strings()["window_title"]
        headline_text.value = strings()["headline"]
        subheadline_text.value = strings()["subheadline"]
        install_section_text.value = strings()["install_section"]
        content_section_text.value = strings()["content_section"]
        status_section_text.value = strings()["status_section"]
        footer_text.value = strings()["footer_support"]
        language_dropdown.label = strings()["language_label"]
        path_field.label = strings()["path_label"]
        path_field.hint_text = strings()["path_hint"]
        browse_button.text = strings()["browse_button"]
        path_help_text.value = strings()["path_help"]
        autodetect_button.text = strings()["autodetect_button"]
        install_button.text = strings()["install_button"]
        kofi_button.text = strings()["footer_kofi_button"]

    def refresh_variant_cards(language: LanguageBundle) -> None:
        available = [name for name in VARIANT_IDS if name in language.variants]
        variant_cards = []
        for variant_name in available:
            variant_cards.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Radio(value=variant_name),
                            ft.Column(
                                controls=[
                                    ft.Text(variant_label(variant_name), weight=ft.FontWeight.W_600, size=15),
                                    ft.Text(
                                        variant_description(variant_name),
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
        variant_group.value = DEFAULT_VARIANT if DEFAULT_VARIANT in language.variants else available[0]

    def handle_language_change(_: ft.ControlEvent) -> None:
        nonlocal selected_language
        selected_language = bundle.languages[language_dropdown.value]
        apply_ui_language()
        refresh_variant_cards(selected_language)
        update_status(
            format_text("status_bundle_detected", version=bundle.version, language=selected_language.label),
            error=False,
        )
        if path_field.value:
            set_install_path(path_field.value)

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
            content=ft.Text(
                message,
                color="#F7FAFC",
                size=13,
            ),
            bgcolor="#8B1E1E" if error else "#1F4A63",
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        page.open(page.snack_bar)

    def set_install_path(path: str | Path) -> None:
        normalized = normalize_install_path(path)
        path_field.value = str(normalized)
        admin_required = path_requires_admin(normalized)
        if admin_required and not is_running_as_admin():
            permission_text.value = strings()["permission_admin_needed"]
            permission_text.color = "#FFB4AB"
        elif admin_required:
            permission_text.value = strings()["permission_admin_ok"]
            permission_text.color = "#A9D18E"
        else:
            permission_text.value = strings()["permission_no_admin"]
            permission_text.color = "#AAB3BB"
        page.update()

    def autodetect_install_path(_: ft.ControlEvent | None = None) -> None:
        candidates = detect_install_paths()
        if candidates:
            set_install_path(candidates[0])
            update_status(
                format_text(
                    "status_autodetected",
                    path=candidates[0],
                    version=bundle.version,
                    language=selected_language.label,
                )
            )
            return
        update_status(
            format_text(
                "status_autodetect_failed",
                version=bundle.version,
                language=selected_language.label,
            ),
            error=True,
        )

    def handle_directory_result(event: ft.FilePickerResultEvent) -> None:
        if event.path:
            set_install_path(event.path)
            update_status(
                format_text(
                    "status_manual_path",
                    path=path_field.value,
                    version=bundle.version,
                    language=selected_language.label,
                )
            )

    file_picker = ft.FilePicker(on_result=handle_directory_result)
    page.overlay.append(file_picker)

    def browse_install_path(_: ft.ControlEvent) -> None:
        file_picker.get_directory_path(dialog_title=strings()["dialog_select_folder"])

    def confirm_install(_: ft.ControlEvent) -> None:
        raw_path = (path_field.value or "").strip()
        if not raw_path:
            show_snackbar(strings()["snackbar_path_required"], error=True)
            return

        variant_name = variant_group.value
        variant_dir = selected_language.variants.get(variant_name)
        if variant_dir is None:
            show_snackbar(strings()["snackbar_variant_missing"], error=True)
            return

        try:
            install_root = normalize_install_path(raw_path)
        except Exception as exc:
            show_snackbar(format_text("snackbar_invalid_path", error=exc), error=True)
            return

        def close_dialog(_: ft.ControlEvent | None = None) -> None:
            if confirm_dialog is not None:
                page.close(confirm_dialog)
            if result_dialog is not None:
                page.close(result_dialog)

        def execute_install(_: ft.ControlEvent) -> None:
            if confirm_dialog is not None:
                page.close(confirm_dialog)
            set_busy(True, format_text("status_installing", variant=variant_label(variant_name), path=install_root))

            try:
                copied_files = install_variant(
                    variant_dir=variant_dir,
                    install_root=install_root,
                    game_language=selected_language.game_language,
                )
            except Exception as exc:
                update_status(format_text("status_install_error", error=exc), error=True)
                show_snackbar(str(exc), error=True)
                set_busy(False)
                return

            set_busy(False)
            update_status(
                format_text(
                    "status_completed",
                    path=install_root,
                    variant=variant_name,
                    count=len(copied_files),
                )
            )
            copied_preview = "\n".join(str(path) for path in copied_files[:6])
            if len(copied_files) > 6:
                copied_preview += "\n" + format_text("dialog_result_more", count=len(copied_files) - 6)

            nonlocal result_dialog
            result_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(strings()["dialog_install_done_title"]),
                content=ft.Text(
                    "\n".join(
                        [
                            format_text("dialog_result_version", version=bundle.version),
                            format_text("dialog_result_language", language=selected_language.label),
                            format_text("dialog_result_destination", path=install_root),
                            format_text("dialog_result_variant", variant=variant_label(variant_name)),
                            format_text("dialog_result_files", count=len(copied_files)),
                            "",
                            copied_preview,
                        ]
                    )
                ),
                actions=[ft.TextButton(strings()["dialog_close"], on_click=close_dialog)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(result_dialog)

        nonlocal confirm_dialog
        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(strings()["dialog_confirm_title"]),
            content=ft.Text(
                "\n".join(
                    [
                        format_text("dialog_confirm_intro", variant=variant_label(variant_name)),
                        "",
                        str(install_root),
                        "",
                        strings()["dialog_confirm_overwrite"],
                    ]
                )
            ),
            actions=[
                ft.TextButton(strings()["dialog_cancel"], on_click=close_dialog),
                ft.FilledButton(strings()["dialog_install"], on_click=execute_install),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        show_snackbar(strings()["snackbar_preparing"])
        page.open(confirm_dialog)

    install_button.on_click = confirm_install
    browse_button.on_click = browse_install_path
    autodetect_button.on_click = autodetect_install_path
    kofi_button.on_click = lambda _: page.launch_url(KO_FI_URL)

    apply_ui_language()
    refresh_variant_cards(selected_language)
    language_dropdown.on_change = handle_language_change

    page.add(
        ft.Container(
            content=ft.Column(
                controls=[
                    headline_text,
                    subheadline_text,
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                install_section_text,
                                language_dropdown,
                                ft.Row(
                                    controls=[
                                        path_field,
                                        browse_button,
                                    ],
                                ),
                                ft.Row(
                                    controls=[
                                        path_help_text,
                                        autodetect_button,
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
                                content_section_text,
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
                                status_section_text,
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
                    ft.Row(
                        controls=[
                            footer_text,
                            kofi_button,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
