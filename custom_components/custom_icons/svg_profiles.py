from __future__ import annotations

import json
import os
from typing import Any, Callable

PROFILE_FILENAME = "_iconset.json"
PROFILE_MARKER_ATTRIBUTE = "data-custom-icons-duotone"

DEFAULT_DUOTONE_PROFILE = {
    "profile": "duotone",
    "primary_color": "oklch(from currentcolor 0.7485 min(c,0.1258) h / 1)",
    "secondary_color": "oklch(from currentcolor 0.8794 min(c,0.0505) h / 1)",
    "primary_opacity": "var(--primary-svg-opacity, 1)",
    "secondary_opacity": "1",
}


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


def _parse_inline_style(style: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for declaration in style.split(";"):
        if ":" not in declaration:
            continue
        name, value = declaration.split(":", 1)
        values[name.strip().lower()] = value.strip()
    return values


def _presentation_value(element, name: str) -> str:
    style_value = _parse_inline_style(element.getAttribute("style")).get(name)
    if style_value is not None:
        return style_value.strip()
    return element.getAttribute(name).strip()


def should_apply_duotone_profile(
    element, role: str, profile: dict[str, str] | None
) -> bool:
    """Return whether an element should inherit the directory duotone profile.

    Explicit non-standard fill/opacity values are treated as intentional per-icon
    exceptions and are left untouched. This lets a collection centralize its
    generated defaults without flattening hand-tuned SVGs.
    """

    if not profile or profile.get("profile") != "duotone":
        return False
    if role not in ("primary", "secondary"):
        return False

    fill = _presentation_value(element, "fill")
    expected_fill = profile[f"{role}_color"]
    if fill and fill != expected_fill and fill.lower() != "currentcolor":
        return False

    opacity = _presentation_value(element, "opacity")
    if opacity:
        expected_opacity = profile[f"{role}_opacity"]
        compatible_opacities = {
            expected_opacity,
            f"var(--{role}-svg-opacity)",
            f"var(--{role}-svg-opacity, 1)",
        }
        if opacity not in compatible_opacities:
            return False

    return True


def mark_duotone_profile_elements(
    document,
    role_resolver: Callable[[Any], str | None],
    profile: dict[str, str] | None,
) -> dict[str, int]:
    """Mark only SVG elements that can safely inherit the duotone profile."""

    counts = {"primary": 0, "secondary": 0, "preserved": 0}
    for element in document.getElementsByTagName("*"):
        role = role_resolver(element)
        if role not in ("primary", "secondary"):
            continue

        if should_apply_duotone_profile(element, role, profile):
            element.setAttribute(PROFILE_MARKER_ATTRIBUTE, role)
            counts[role] += 1
        else:
            if element.hasAttribute(PROFILE_MARKER_ATTRIBUTE):
                element.removeAttribute(PROFILE_MARKER_ATTRIBUTE)
            counts["preserved"] += 1

    return counts


def build_svg_profile_css(profile: dict[str, str] | None) -> str:
    """Build CSS injected into an SVG body for marked profile elements."""

    if not profile:
        return ""
    if profile.get("profile") != "duotone":
        raise SvgProfileError(f"unsupported SVG profile: {profile.get('profile')}")

    primary = f'[{PROFILE_MARKER_ATTRIBUTE}="primary"]'
    secondary = f'[{PROFILE_MARKER_ATTRIBUTE}="secondary"]'

    return f"""
{primary},
{primary} * {{
  fill: var(--custom-icons-duotone-primary-color, {profile['primary_color']}) !important;
}}
{primary} {{
  opacity: var(--custom-icons-duotone-primary-opacity, {profile['primary_opacity']}) !important;
}}
{secondary},
{secondary} * {{
  fill: var(--custom-icons-duotone-secondary-color, {profile['secondary_color']}) !important;
}}
{secondary} {{
  opacity: var(--custom-icons-duotone-secondary-opacity, {profile['secondary_opacity']}) !important;
}}
""".strip()
