from __future__ import annotations

import re

from localization_tools import Entry, GlobalIniData


TITLE_TOKEN_RE = re.compile(r"^(?P<prefix>.*?)(?:_)?(?P<token>title)(?P<suffix>(?:_[^=]+)?)$", re.IGNORECASE)
DESC_TOKEN_RE = re.compile(r"^(?P<prefix>.*?)(?:_)?(?P<token>desc|description)(?P<suffix>(?:_[^=]+)?)$", re.IGNORECASE)
LOCATION_PLACEHOLDER_RE = re.compile(r"~mission\(Location\|(?:Address|name)\)", re.IGNORECASE)
DESTINATION_PLACEHOLDER_RE = re.compile(r"~mission\(Destination\|(?:Address|name)\)", re.IGNORECASE)
MULTI_LOCATION_RE = re.compile(r"~mission\(Location\d+\|", re.IGNORECASE)
MULTI_DESTINATION_RE = re.compile(r"~mission\(Destination\d+\|", re.IGNORECASE)

TRANSPORT_KEY_MARKERS = (
    "delivery",
    "cargo",
    "haul",
    "retrievecargo",
    "recovercargo",
    "refuel",
    "transport",
    "salvage",
)
MULTI_TO_SINGLE_TOKEN_RE = re.compile(r"~mission\(MultiToSingleToken\)", re.IGNORECASE)
SINGLE_TO_MULTI_TOKEN_RE = re.compile(r"~mission\(SingleToMultiToken\)", re.IGNORECASE)


def _build_signature(key: str) -> tuple[str, str] | None:
    title_match = TITLE_TOKEN_RE.match(key)
    if title_match is not None:
        return title_match.group("prefix").lower(), title_match.group("suffix").lower()

    desc_match = DESC_TOKEN_RE.match(key)
    if desc_match is not None:
        return desc_match.group("prefix").lower(), desc_match.group("suffix").lower()

    return None


def _looks_like_transport_key(key: str) -> bool:
    normalized = key.lower().replace("_", "")
    return any(marker in normalized for marker in TRANSPORT_KEY_MARKERS)


def _transport_suffix_from_title_key(key: str) -> str | None:
    normalized = key.lower().replace("_", "")
    if "multitosingle" in normalized:
        return " | ##transport_to## ~mission(Destination|name)"
    if "singletomulti" in normalized:
        return " | ##transport_from## ~mission(Location|name)"
    if "atob" in normalized:
        return " | ~mission(Location|name) > ~mission(Destination|name)"
    return None


def _transport_suffix_for_shape(*, has_location: bool, has_destination: bool, has_multi_location: bool, has_multi_destination: bool) -> str | None:
    if has_multi_location and not has_multi_destination and has_destination:
        return " | ##transport_to## ~mission(Destination|name)"
    if has_multi_destination and not has_multi_location and has_location:
        return " | ##transport_from## ~mission(Location|name)"
    if has_multi_location and has_multi_destination:
        return None
    if has_location and has_destination:
        return " | ~mission(Location|name) > ~mission(Destination|name)"
    if has_location:
        return " | ##transport_from## ~mission(Location|name)"
    if has_destination:
        return " | ##transport_to## ~mission(Destination|name)"
    return None


def _transport_suffix_from_description(value: str) -> str | None:
    if MULTI_TO_SINGLE_TOKEN_RE.search(value):
        return " | ##transport_to## ~mission(Destination|name)"
    if SINGLE_TO_MULTI_TOKEN_RE.search(value):
        return " | ##transport_from## ~mission(Location|name)"

    has_location = LOCATION_PLACEHOLDER_RE.search(value) is not None
    has_destination = DESTINATION_PLACEHOLDER_RE.search(value) is not None
    has_multi_location = MULTI_LOCATION_RE.search(value) is not None
    has_multi_destination = MULTI_DESTINATION_RE.search(value) is not None
    return _transport_suffix_for_shape(
        has_location=has_location,
        has_destination=has_destination,
        has_multi_location=has_multi_location,
        has_multi_destination=has_multi_destination,
    )


def generate_transport_overlay_data(*, english_data: GlobalIniData) -> GlobalIniData:
    descriptions_by_signature: dict[tuple[str, str], str] = {}
    for entry in english_data.entries:
        signature = _build_signature(entry.key)
        if signature is None:
            continue
        if DESC_TOKEN_RE.match(entry.key):
            descriptions_by_signature[signature] = entry.value

    generated_entries: list[Entry] = []
    for entry in english_data.entries:
        if not TITLE_TOKEN_RE.match(entry.key):
            continue
        if not _looks_like_transport_key(entry.key):
            continue

        signature = _build_signature(entry.key)
        if signature is None:
            continue
        description_value = descriptions_by_signature.get(signature)

        suffix = _transport_suffix_from_title_key(entry.key)
        if suffix is None and description_value is not None:
            suffix = _transport_suffix_from_description(description_value)
        if suffix is None:
            continue

        generated_entries.append(Entry(key=entry.key, value=suffix))

    generated_mapping = {entry.key: entry.value for entry in generated_entries}
    return GlobalIniData(entries=generated_entries, mapping=generated_mapping)
