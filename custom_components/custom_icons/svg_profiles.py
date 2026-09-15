from __future__ import annotations

import json
import os
from typing import Any

PROFILE_FILENAME = "_iconset.json"

DEFAULT_DUOTONE_PROFILE = {
    "profile": "duotone",
    "primary_color": "oklch(from currentcolor 0.7485 min(c,0.1258) h / 1)",
    "secondary_color": "oklch(from currentcolor 0.8794 min(c,0.0505) h / 1)",
    "primary_opacity": "var(--primary-svg-opacity, 1)",
    "secondary_opacity": "1",
}

_PRIMARY_SELECTORS = (
    '#primary',
    '[id^="primary-"]',
    '[data-name="primary"]',
    '.primary',
    '.fa-primary',
)

_SECONDARY_SELECTORS = (
    '#secondary',
    '[id^="secondary-"]',
    '[data-name="secondary"]',
    '.secondary',
    '.fa-secondary',
)


class SvgProfileError(ValueError):
    """Raised when a local SVG profile is invalid."""


def _css_value(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SvgProfileError(f"{name} must be a non-empty string")

    value = value.strip()
    lowered = value.lower()
    if any(token in value for token in ("<", ">", "{", "}", ";", "\n", "\r")):
        raise SvgProfileError(f"{name} contains unsafe CSS characters")
    if any(token in lowered for token in ("url(", "expression(", "@import")):
        raise SvgProfileError(f"{name} contains an unsupported CSS function")
    return value


def normalize_svg_profile(data: Any) -> dict[str, str] | None:
    """Validate a profile document and return normalized settings."""

    if data is None:
        return None
    if not isinstance(data, dict):
        raise SvgProfileError("profile document must be a JSON object")

    profile_name = data.get("profile")
    if profile_name in (None, "", "none"):
        return None
    if profile_name != "duotone":
        raise SvgProfileError(f"unsupported SVG profile: {profile_name}")

    profile = DEFAULT_DUOTONE_PROFILE.copy()
    for key in (
        "primary_color",
        "secondary_color",
        "primary_opacity",
        "secondary_opacity",
    ):
        if key in data:
            profile[key] = _css_value(key, data[key])

    return profile


def load_svg_profile(path: str) -> dict[str, str] | None:
    """Load and validate a profile JSON file."""

    with open(path, encoding="utf-8") as fp:
        return normalize_svg_profile(json.load(fp))


def find_svg_profile(icon_path: str, icon_root: str) -> tuple[dict[str, str] | None, str | None]:
    """Find the nearest inherited _iconset.json between an icon and icon root."""

    root = os.path.realpath(icon_root)
    current = os.path.dirname(os.path.realpath(icon_path))

    try:
        if os.path.commonpath((root, current)) != root:
            return None, None
    except ValueError:
        return None, None

    while True:
        candidate = os.path.join(current, PROFILE_FILENAME)
        if os.path.isfile(candidate):
            return load_svg_profile(candidate), candidate
        if current == root:
            break
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return None, None


def _selector_list(selectors: tuple[str, ...]) -> str:
    return ",\n".join(selectors)


def _with_descendants(selectors: tuple[str, ...]) -> str:
    return _selector_list((*selectors, *(f"{selector} *" for selector in selectors)))


def build_svg_profile_css(profile: dict[str, str] | None) -> str:
    """Build CSS injected into an SVG body for the selected profile."""

    if not profile:
        return ""
    if profile.get("profile") != "duotone":
        raise SvgProfileError(f"unsupported SVG profile: {profile.get('profile')}")

    primary_fill = _with_descendants(_PRIMARY_SELECTORS)
    secondary_fill = _with_descendants(_SECONDARY_SELECTORS)
    primary_role = _selector_list(_PRIMARY_SELECTORS)
    secondary_role = _selector_list(_SECONDARY_SELECTORS)

    return f"""
{primary_fill} {{
  fill: var(--custom-icons-duotone-primary-color, {profile['primary_color']}) !important;
}}
{primary_role} {{
  opacity: var(--custom-icons-duotone-primary-opacity, {profile['primary_opacity']}) !important;
}}
{secondary_fill} {{
  fill: var(--custom-icons-duotone-secondary-color, {profile['secondary_color']}) !important;
}}
{secondary_role} {{
  opacity: var(--custom-icons-duotone-secondary-opacity, {profile['secondary_opacity']}) !important;
}}
""".strip()
