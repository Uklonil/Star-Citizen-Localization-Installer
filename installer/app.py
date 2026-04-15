from __future__ import annotations

import argparse
import ctypes
import json
import sys
import tempfile
from pathlib import Path

import flet as ft

try:
    import flet_desktop.version  # noqa: F401
except ModuleNotFoundError:
    pass

try:
    from .installer_core import (
        AssetBundle,
        DEFAULT_VARIANT,
        LanguageBundle,
        VARIANT_IDS,
        detect_install_paths,
        discover_asset_bundle,
        fetch_remote_asset_bundle,
        install_variant,
        is_running_as_admin,
        load_asset_bundle,
        normalize_install_path,
        path_requires_admin,
        run_elevated_process,
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
            AssetBundle,
            DEFAULT_VARIANT,
            LanguageBundle,
            VARIANT_IDS,
            detect_install_paths,
            discover_asset_bundle,
            fetch_remote_asset_bundle,
            install_variant,
            is_running_as_admin,
            load_asset_bundle,
            normalize_install_path,
            path_requires_admin,
            run_elevated_process,
        )
    except ImportError:
        from installer_core import (
            AssetBundle,
            DEFAULT_VARIANT,
            LanguageBundle,
            VARIANT_IDS,
            detect_install_paths,
            discover_asset_bundle,
            fetch_remote_asset_bundle,
            install_variant,
            is_running_as_admin,
            load_asset_bundle,
            normalize_install_path,
            path_requires_admin,
            run_elevated_process,
        )

DEFAULT_UI_LANGUAGE = "en"
_UI_CACHE: dict[str, dict[str, str]] = {}
KO_FI_URL = "https://ko-fi.com/uklonil"
FONT_FAMILY = "Orbitron"


def _app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _ui_texts_dir() -> Path:
    return _app_base_dir() / "installer" / "ui_texts"


def _assets_dir() -> Path:
    return _app_base_dir() / "installer" / "assets"


def _orbitron_font_path() -> Path:
    return _assets_dir() / "Orbitron-VariableFont_wght.ttf"


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


def _show_message_box(title: str, message: str, *, error: bool = False) -> None:
    style = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(None, message, title, style)


def run_elevated_install_mode(args: argparse.Namespace) -> int:
    ui_language = args.ui_language or args.language
    ui_strings = load_ui_strings(ui_language)

    try:
        bundle = load_asset_bundle(source=args.bundle_source, version=args.bundle_version)
        selected_language = bundle.languages[args.language]
        variant = selected_language.variants[args.variant]
        install_root = normalize_install_path(args.install_path)
        copied_files = install_variant(
            variant=variant,
            install_root=install_root,
            game_language=selected_language.game_language,
            language_code=selected_language.code,
        )
        result = {
            "ok": True,
            "version": bundle.version,
            "language": selected_language.label,
            "variant": args.variant,
            "path": str(install_root),
            "copied_files": [str(path) for path in copied_files],
        }
    except Exception as exc:
        result = {
            "ok": False,
            "error": str(exc),
        }

    if args.result_file:
        Path(args.result_file).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

    if not args.result_file and not result["ok"]:
        _show_message_box(ui_strings["dialog_install_failed_title"], result["error"], error=True)

    return 0 if result["ok"] else 1


def main(page: ft.Page) -> None:
    bundle = discover_asset_bundle()
    window_icon = _assets_dir() / "app-icon.ico"
    if window_icon.is_file():
        page.window.icon = str(window_icon)
    orbitron_font = _orbitron_font_path()
    if orbitron_font.is_file():
        page.fonts = {FONT_FAMILY: str(orbitron_font)}
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window.width = 920
    page.window.height = 760
    page.window.resizable = False
    page.window.maximizable = False
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.ORANGE, font_family=FONT_FAMILY)
    page.bgcolor = "#04050A"
    page.scroll = ft.ScrollMode.AUTO

    available_languages = list(bundle.languages.values())
    default_language = next((language for language in available_languages if language.code == "en"), available_languages[0])
    selected_language: LanguageBundle = default_language
    available_variants = [name for name in VARIANT_IDS if name in selected_language.variants]
    default_variant = DEFAULT_VARIANT if DEFAULT_VARIANT in selected_language.variants else available_variants[0]

    def strings() -> dict[str, str]:
        return load_ui_strings(selected_language.code)

    def format_text(key: str, **kwargs: object) -> str:
        return strings()[key].format(**kwargs)

    def bundle_source_label(bundle_source: str) -> str:
        if bundle_source == "remote":
            return strings()["bundle_source_remote"]
        return strings()["bundle_source_local"]

    def bundle_status_text(current_bundle: AssetBundle) -> str:
        return format_text(
            "bundle_badge",
            version=current_bundle.version,
            source=bundle_source_label(current_bundle.source),
        )

    status_text = ft.Text(value="", size=13, color="#D6DEE8", font_family=FONT_FAMILY)
    permission_text = ft.Text(size=12, color="#AAB3BB", font_family=FONT_FAMILY)
    progress_ring = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False, color="#FFAA2B")
    path_field = ft.TextField(
        label="",
        hint_text="",
        expand=True,
        autofocus=True,
        border_color="#5A3A14",
        focused_border_color="#FF9A1F",
        bgcolor="#0C1018",
        color="#F5F7FA",
        cursor_color="#FFB347",
        label_style=ft.TextStyle(font_family=FONT_FAMILY, color="#FFB347", size=12),
        hint_style=ft.TextStyle(font_family=FONT_FAMILY, color="#697488", size=12),
        text_style=ft.TextStyle(font_family=FONT_FAMILY, color="#F5F7FA", size=13),
    )
    headline_text = ft.Text(size=28, weight=ft.FontWeight.BOLD, font_family=FONT_FAMILY, color="#FFF3D8")
    subheadline_text = ft.Text(size=14, color="#C7CDD3", font_family=FONT_FAMILY)
    install_section_text = ft.Text(size=18, weight=ft.FontWeight.W_600, font_family=FONT_FAMILY, color="#FFBF5A")
    path_help_text = ft.Text(size=12, color="#93A0B4", expand=True, font_family=FONT_FAMILY)
    content_section_text = ft.Text(size=18, weight=ft.FontWeight.W_600, font_family=FONT_FAMILY, color="#FFBF5A")
    status_section_text = ft.Text(size=18, weight=ft.FontWeight.W_600, font_family=FONT_FAMILY, color="#FFBF5A")
    footer_text = ft.Text(size=11, color="#77849A", font_family=FONT_FAMILY)
    bundle_badge = ft.Text(
        bundle_status_text(bundle),
        font_family=FONT_FAMILY,
        size=11,
        color="#7FD2FF",
        weight=ft.FontWeight.W_700,
    )
    language_dropdown = ft.Dropdown(
        label="",
        value=default_language.code,
        options=[ft.dropdown.Option(language.code, language.label) for language in available_languages],
        width=260,
        bgcolor="#0C1018",
        border_color="#5A3A14",
        focused_border_color="#FF9A1F",
        color="#F5F7FA",
        label_style=ft.TextStyle(font_family=FONT_FAMILY, color="#FFB347", size=12),
        text_style=ft.TextStyle(font_family=FONT_FAMILY, color="#F5F7FA", size=13),
    )
    variant_group = ft.RadioGroup(content=ft.Column(spacing=10), value=default_variant)
    install_button = ft.FilledButton(
        text="",
        icon=ft.Icons.DOWNLOAD_DONE,
        style=ft.ButtonStyle(
            bgcolor={"default": "#FF8E1A", "disabled": "#5C4A2E"},
            color={"default": "#091018", "disabled": "#D4B48A"},
            text_style=ft.TextStyle(font_family=FONT_FAMILY, size=14, weight=ft.FontWeight.W_700),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=18,
        ),
    )
    browse_button = ft.OutlinedButton(
        "",
        icon=ft.Icons.FOLDER_OPEN,
        style=ft.ButtonStyle(
            color="#FFD18A",
            side={"default": ft.BorderSide(1, "#7A4B14")},
            text_style=ft.TextStyle(font_family=FONT_FAMILY, size=12, weight=ft.FontWeight.W_600),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )
    autodetect_button = ft.TextButton(
        "",
        icon=ft.Icons.MY_LOCATION,
        style=ft.ButtonStyle(
            color="#7FD2FF",
            text_style=ft.TextStyle(font_family=FONT_FAMILY, size=12, weight=ft.FontWeight.W_600),
        ),
    )
    check_updates_button = ft.TextButton(
        "",
        icon=ft.Icons.CLOUD_DOWNLOAD,
        style=ft.ButtonStyle(
            color="#7FD2FF",
            text_style=ft.TextStyle(font_family=FONT_FAMILY, size=12, weight=ft.FontWeight.W_600),
        ),
    )
    kofi_button = ft.TextButton(
        icon=ft.Icons.OPEN_IN_NEW,
        style=ft.ButtonStyle(
            color="#FFB347",
            text_style=ft.TextStyle(font_family=FONT_FAMILY, size=12, weight=ft.FontWeight.W_600),
        ),
    )
    confirm_dialog: ft.AlertDialog | None = None
    result_dialog: ft.AlertDialog | None = None

    def panel(title: ft.Text, content: ft.Control) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[title, content], spacing=12),
            padding=18,
            border_radius=18,
            border=ft.border.all(1, "#3C4658"),
            bgcolor="#0A0E16",
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#111722", "#090C13"],
            ),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=16, color="#33000000", offset=ft.Offset(0, 8)),
        )

    def variant_label(variant_name: str) -> str:
        return strings()[f"variant_{variant_name.replace('-', '_')}_label"]

    def variant_description(variant_name: str) -> str:
        return strings()[f"variant_{variant_name.replace('-', '_')}_desc"]

    def update_status(message: str, *, error: bool = False) -> None:
        status_text.value = message
        status_text.color = "#FFB4AB" if error else "#C7CDD3"
        page.update()

    def show_snackbar(message: str, *, error: bool = False) -> None:
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color="#F7FAFC", size=13, font_family=FONT_FAMILY),
            bgcolor="#8B1E1E" if error else "#1F4A63",
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        page.open(page.snack_bar)

    def update_bundle_ui() -> None:
        bundle_badge.value = bundle_status_text(bundle)
        page.update()

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
        check_updates_button.text = strings()["check_updates_button"]
        install_button.text = strings()["install_button"]
        kofi_button.text = strings()["footer_kofi_button"]
        update_bundle_ui()

    def refresh_variant_cards(language: LanguageBundle) -> None:
        available = [name for name in VARIANT_IDS if name in language.variants]
        variant_cards = []
        for variant_name in available:
            def select_variant(_: ft.ControlEvent, selected_variant: str = variant_name) -> None:
                variant_group.value = selected_variant
                page.update()

            variant_cards.append(
                ft.Container(
                    ink=True,
                    on_click=select_variant,
                    content=ft.Row(
                        controls=[
                            ft.Radio(value=variant_name),
                            ft.Column(
                                controls=[
                                    ft.Text(variant_label(variant_name), weight=ft.FontWeight.W_600, size=15, font_family=FONT_FAMILY),
                                    ft.Text(variant_description(variant_name), size=12, color="#B8C0C7", font_family=FONT_FAMILY),
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

    def set_bundle(new_bundle: AssetBundle, *, preferred_language_code: str | None = None) -> None:
        nonlocal bundle, selected_language
        bundle = new_bundle
        languages = list(bundle.languages.values())
        if not languages:
            raise ValueError("El paquete seleccionado no contiene idiomas instalables.")

        preferred_code = preferred_language_code or selected_language.code
        selected_language = bundle.languages.get(preferred_code, bundle.languages.get("en", languages[0]))
        language_dropdown.options = [ft.dropdown.Option(language.code, language.label) for language in languages]
        language_dropdown.value = selected_language.code
        apply_ui_language()
        refresh_variant_cards(selected_language)
        if path_field.value:
            set_install_path(path_field.value)
        page.update()

    def handle_language_change(_: ft.ControlEvent) -> None:
        nonlocal selected_language
        selected_language = bundle.languages[language_dropdown.value]
        apply_ui_language()
        refresh_variant_cards(selected_language)
        update_status(
            format_text(
                "status_bundle_detected",
                version=bundle.version,
                language=selected_language.label,
                source=bundle_source_label(bundle.source),
            ),
            error=False,
        )
        if path_field.value:
            set_install_path(path_field.value)

    def set_busy(is_busy: bool, message: str | None = None) -> None:
        install_button.disabled = is_busy
        browse_button.disabled = is_busy
        autodetect_button.disabled = is_busy
        check_updates_button.disabled = is_busy
        language_dropdown.disabled = is_busy
        progress_ring.visible = is_busy
        if message is not None:
            update_status(message)
        page.update()

    def show_result_dialog(*, version: str, language: str, variant_name: str, install_root: Path, copied_files: list[str]) -> None:
        copied_preview = "\n".join(copied_files[:6])
        if len(copied_files) > 6:
            copied_preview += "\n" + format_text("dialog_result_more", count=len(copied_files) - 6)

        nonlocal result_dialog
        result_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(strings()["dialog_install_done_title"]),
            content=ft.Text(
                "\n".join(
                    [
                        format_text("dialog_result_version", version=version),
                        format_text("dialog_result_language", language=language),
                        format_text("dialog_result_destination", path=install_root),
                        format_text("dialog_result_variant", variant=variant_label(variant_name)),
                        format_text("dialog_result_files", count=len(copied_files)),
                        "",
                        copied_preview,
                    ]
                )
            ),
            actions=[ft.TextButton(strings()["dialog_close"], on_click=close_dialog, style=ft.ButtonStyle(text_style=ft.TextStyle(font_family=FONT_FAMILY)))],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor="#0B0F17",
        )
        page.open(result_dialog)

    def close_dialog(_: ft.ControlEvent | None = None) -> None:
        if confirm_dialog is not None:
            page.close(confirm_dialog)
        if result_dialog is not None:
            page.close(result_dialog)

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
                    source=bundle_source_label(bundle.source),
                )
            )
            return
        update_status(
            format_text(
                "status_autodetect_failed",
                version=bundle.version,
                language=selected_language.label,
                source=bundle_source_label(bundle.source),
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
                    source=bundle_source_label(bundle.source),
                )
            )

    def check_updates(_: ft.ControlEvent) -> None:
        set_busy(True, strings()["status_checking_updates"])
        try:
            remote_bundle = fetch_remote_asset_bundle()
        except Exception as exc:
            update_status(format_text("status_update_error", error=exc), error=True)
            show_snackbar(str(exc), error=True)
            set_busy(False)
            return

        current_version = bundle.version
        current_source = bundle.source
        if remote_bundle.version == current_version and current_source == "remote":
            update_status(format_text("status_update_current", version=remote_bundle.version))
            show_snackbar(strings()["snackbar_update_current"])
            set_busy(False)
            return

        if remote_bundle.version == current_version and current_source == "local":
            set_bundle(remote_bundle)
            update_status(format_text("status_update_same_version", version=remote_bundle.version))
            show_snackbar(strings()["snackbar_update_same_version"])
            set_busy(False)
            return

        set_bundle(remote_bundle)
        update_status(
            format_text(
                "status_update_applied",
                version=remote_bundle.version,
                previous=current_version,
            )
        )
        show_snackbar(format_text("snackbar_update_applied", version=remote_bundle.version))
        set_busy(False)

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
        variant = selected_language.variants.get(variant_name)
        if variant is None:
            show_snackbar(strings()["snackbar_variant_missing"], error=True)
            return

        try:
            install_root = normalize_install_path(raw_path)
        except Exception as exc:
            show_snackbar(format_text("snackbar_invalid_path", error=exc), error=True)
            return

        def execute_install(_: ft.ControlEvent) -> None:
            if confirm_dialog is not None:
                page.close(confirm_dialog)
            set_busy(True, format_text("status_installing", variant=variant_label(variant_name), path=install_root))

            if path_requires_admin(install_root) and not is_running_as_admin():
                with tempfile.NamedTemporaryFile(
                    prefix="sc-localization-install-",
                    suffix=".json",
                    delete=False,
                ) as temp_handle:
                    result_file = Path(temp_handle.name)
                arguments = [
                    "--elevated-install",
                    "--bundle-source",
                    bundle.source,
                    "--bundle-version",
                    bundle.version,
                    "--language",
                    selected_language.code,
                    "--variant",
                    variant_name,
                    "--install-path",
                    str(install_root),
                    "--ui-language",
                    selected_language.code,
                    "--result-file",
                    str(result_file),
                ]
                if not getattr(sys, "frozen", False):
                    arguments.insert(0, str(Path(__file__).resolve()))

                update_status(format_text("status_requesting_elevation", path=install_root))
                try:
                    exit_code = run_elevated_process(
                        executable_path=Path(sys.executable),
                        arguments=arguments,
                        working_directory=_app_base_dir(),
                    )
                except PermissionError:
                    update_status(strings()["status_elevation_cancelled"], error=True)
                    show_snackbar(strings()["snackbar_elevation_cancelled"], error=True)
                    set_busy(False)
                    return
                except Exception as exc:
                    update_status(format_text("status_install_error", error=exc), error=True)
                    show_snackbar(str(exc), error=True)
                    set_busy(False)
                    return

                if not result_file.is_file():
                    update_status(strings()["status_elevated_result_missing"], error=True)
                    show_snackbar(strings()["status_elevated_result_missing"], error=True)
                    set_busy(False)
                    return

                result_payload = json.loads(result_file.read_text(encoding="utf-8"))
                result_file.unlink(missing_ok=True)

                if exit_code != 0 or not result_payload.get("ok"):
                    error_message = str(result_payload.get("error", strings()["status_elevated_result_missing"]))
                    update_status(format_text("status_install_error", error=error_message), error=True)
                    show_snackbar(error_message, error=True)
                    set_busy(False)
                    return

                copied_files = [str(path) for path in result_payload.get("copied_files", [])]
                set_busy(False)
                update_status(
                    format_text(
                        "status_completed",
                        path=install_root,
                        variant=variant_name,
                        count=len(copied_files),
                    )
                )
                show_result_dialog(
                    version=str(result_payload.get("version", bundle.version)),
                    language=str(result_payload.get("language", selected_language.label)),
                    variant_name=variant_name,
                    install_root=install_root,
                    copied_files=copied_files,
                )
                return

            try:
                copied_files = install_variant(
                    variant=variant,
                    install_root=install_root,
                    game_language=selected_language.game_language,
                    language_code=selected_language.code,
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
            show_result_dialog(
                version=bundle.version,
                language=selected_language.label,
                variant_name=variant_name,
                install_root=install_root,
                copied_files=[str(path) for path in copied_files],
            )

        nonlocal confirm_dialog
        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(strings()["dialog_confirm_title"], font_family=FONT_FAMILY, color="#FFD18A"),
            content=ft.Text(
                "\n".join(
                    [
                        format_text("dialog_confirm_intro", variant=variant_label(variant_name)),
                        "",
                        str(install_root),
                        "",
                        strings()["dialog_confirm_overwrite"],
                    ]
                ),
                font_family=FONT_FAMILY,
                color="#DDE6F2",
            ),
            bgcolor="#0B0F17",
            actions=[
                ft.TextButton(strings()["dialog_cancel"], on_click=close_dialog, style=ft.ButtonStyle(text_style=ft.TextStyle(font_family=FONT_FAMILY))),
                ft.FilledButton(strings()["dialog_install"], on_click=execute_install, style=ft.ButtonStyle(text_style=ft.TextStyle(font_family=FONT_FAMILY, weight=ft.FontWeight.W_700))),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        show_snackbar(strings()["snackbar_preparing"])
        page.open(confirm_dialog)

    install_button.on_click = confirm_install
    browse_button.on_click = browse_install_path
    autodetect_button.on_click = autodetect_install_path
    check_updates_button.on_click = check_updates
    kofi_button.on_click = lambda _: page.launch_url(KO_FI_URL)

    apply_ui_language()
    refresh_variant_cards(selected_language)
    language_dropdown.on_change = handle_language_change

    page.add(
        ft.Container(
            expand=True,
            padding=18,
            bgcolor="#04050A",
            content=ft.Container(
                expand=True,
                border_radius=26,
                border=ft.border.all(2, "#272D3A"),
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_center,
                    end=ft.alignment.bottom_center,
                    colors=["#090B12", "#030409"],
                ),
                padding=10,
                content=ft.Container(
                    expand=True,
                    border_radius=22,
                    border=ft.border.all(1.2, "#8B5319"),
                    padding=16,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(height=5, expand=3, border_radius=6, bgcolor="#39435A"),
                                    ft.Container(height=5, expand=4, border_radius=6, gradient=ft.LinearGradient(colors=["#6A4A1E", "#FF9A1F", "#6A4A1E"])),
                                    ft.Container(height=5, expand=3, border_radius=6, bgcolor="#39435A"),
                                ],
                                spacing=14,
                            ),
                            ft.Container(
                                expand=True,
                                border_radius=18,
                                border=ft.border.all(1, "#3F2710"),
                                padding=20,
                                content=ft.Column(
                                    controls=[
                                        ft.Row(
                                            controls=[
                                                ft.Column(
                                                    controls=[
                                                        headline_text,
                                                        subheadline_text,
                                                    ],
                                                    spacing=6,
                                                    expand=True,
                                                ),
                                                ft.Container(
                                                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                                                    border_radius=10,
                                                    bgcolor="#111824",
                                                    border=ft.border.all(1, "#36506B"),
                                                    content=bundle_badge,
                                                ),
                                            ],
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            vertical_alignment=ft.CrossAxisAlignment.START,
                                        ),
                                        panel(
                                            install_section_text,
                                            ft.Column(
                                                controls=[
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
                                                            check_updates_button,
                                                        ],
                                                    ),
                                                    permission_text,
                                                ],
                                                spacing=10,
                                            ),
                                        ),
                                        panel(
                                            content_section_text,
                                            variant_group,
                                        ),
                                        panel(
                                            status_section_text,
                                            status_text,
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
                                        ft.Row(
                                            controls=[
                                                ft.Container(height=6, width=96, border_radius=6, bgcolor="#26A7FF"),
                                                ft.Container(expand=True),
                                                ft.Container(height=6, width=96, border_radius=6, bgcolor="#26A7FF"),
                                            ],
                                        ),
                                    ],
                                    spacing=18,
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                            ),
                        ],
                        spacing=14,
                    ),
                ),
            ),
        )
    )

    update_status(
        format_text(
            "status_bundle_detected",
            version=bundle.version,
            language=selected_language.label,
            source=bundle_source_label(bundle.source),
        )
    )
    autodetect_install_path()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--elevated-install", action="store_true")
    parser.add_argument("--bundle-source")
    parser.add_argument("--bundle-version")
    parser.add_argument("--language")
    parser.add_argument("--variant")
    parser.add_argument("--install-path")
    parser.add_argument("--ui-language")
    parser.add_argument("--result-file")
    cli_args, _ = parser.parse_known_args()

    if cli_args.elevated_install:
        raise SystemExit(run_elevated_install_mode(cli_args))

    ft.app(target=main)
