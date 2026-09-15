from typing import TypedDict
from xml.dom import minidom
from homeassistant.core import HomeAssistant

from .svg_profiles import build_svg_profile_css, mark_duotone_profile_elements


class IconData(TypedDict):
    renderer: str | None


class IconSetInfo(TypedDict):
    name: str
    prefix: str
    total: int
    active: bool
    sample_icons: list[IconData]


class IconListItem(TypedDict):
    name: str
    keywords: list[str]


class IconSetCollection:

    def flush(self) -> None:
        pass

    async def sets(self, hass: HomeAssistant) -> dict[str, IconSetInfo]:
        return {}

    async def prefixes(self, hass: HomeAssistant) -> list[str]:
        return []

    async def list(self, hass: HomeAssistant, prefix: str) -> list[IconListItem]:
        return []

    async def icon(
        self, hass: HomeAssistant, prefix: str, icon: str
    ) -> IconData | None:
        pass


def _element_role(element) -> str | None:
    classes = element.getAttribute("class").split()
    if "secondary" in classes or "fa-secondary" in classes:
        return "secondary"
    if "primary" in classes or "fa-primary" in classes:
        return "primary"

    element_id = element.getAttribute("id").lower()
    data_name = element.getAttribute("data-name").lower()

    if element_id == "secondary" or element_id.startswith("secondary-"):
        return "secondary"
    if data_name == "secondary":
        return "secondary"
    if element_id == "primary" or element_id.startswith("primary-"):
        return "primary"
    if data_name == "primary":
        return "primary"
    return None


def process_svg(svg, profile: dict[str, str] | None = None) -> IconData:

    body = svg

    if hasattr(body, "decode"):
        body = body.decode("utf-8")
    body = str(body)

    s = minidom.parseString(body)
    sumpath = ""
    path = ""
    path2 = ""

    for p in s.getElementsByTagName("path"):
        d = p.getAttribute("d")
        sumpath += d
        role = _element_role(p)
        if role == "primary":
            path = d
        elif role == "secondary":
            path2 = d

    path = path or sumpath

    if profile:
        mark_duotone_profile_elements(s, _element_role, profile)

    body = "".join(
        (n.toprettyxml() for n in s.getElementsByTagName("svg")[0].childNodes)
    )

    style = ".fa-secondary{opacity:.4}"
    profile_css = build_svg_profile_css(profile)
    if profile_css:
        style += "\n" + profile_css
    body = f"<defs><style>{style}</style></defs>" + body

    view_box = s.getElementsByTagName("svg")[0].getAttribute("viewBox").split()
    if not view_box:
        view_box = ["0", "0", "24", "24"]

    icon_data = {
        "renderer": None,
        "viewBox": view_box,
        "path": path,
        "path2": path2,
        "body": body,
    }

    return icon_data
