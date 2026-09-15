import asyncio
import os
import logging
import random
from homeassistant.core import HomeAssistant

from .iconset_base import (
    IconSetCollection,
    IconData,
    IconSetInfo,
    IconListItem,
    process_svg,
)
from .const import DOMAIN, ICON_PATH
from .svg_profiles import SvgProfileError, find_svg_profile

LOGGER = logging.getLogger(__name__)


def list_icons(root):
    icon_list = []
    for dirpath, dirnames, filenames in os.walk(root):
        subdir = dirpath.removeprefix(root).lstrip("/")
        icon_list.extend(
            [
                {"name": os.path.join(subdir, fn.removesuffix(".svg"))}
                for fn in filenames
                if fn.endswith(".svg") and not fn.endswith("-webfont.svg")
            ]
        )
    return icon_list


def resolve_icon_path(root: str, icon: str) -> str:
    root = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, icon + ".svg"))

    try:
        if os.path.commonpath((root, path)) != root:
            raise ValueError(f"Icon path escapes local icon root: {icon}")
    except ValueError as err:
        raise ValueError(f"Invalid local icon path: {icon}") from err

    return path


def read_icon(path: str) -> str:
    with open(path, encoding="utf-8") as fp:
        return fp.read()


class LocalSet(IconSetCollection):

    def __init__(self):
        self.cache = []
        self.profile_cache = {}

    def flush(self) -> None:
        self.cache = []
        self.profile_cache = {}

    async def sets(self, hass: HomeAssistant) -> dict[str, IconSetInfo]:
        prefix = "local"
        icons = await self.list(hass, prefix)

        config = hass.config_entries.async_entries(DOMAIN)
        config = config[0] if config else {}

        samples = random.sample(icons, min(6, len(icons)))
        samples = [await self.icon(hass, prefix, icon["name"]) for icon in samples]

        return {
            prefix: {
                "name": "Local",
                "prefix": prefix,
                "total": len(icons),
                "active": config.data.get(prefix, False),
                "sample_icons": samples,
            }
        }

    async def prefixes(self, hass: HomeAssistant) -> list[str]:
        return ["local"]

    async def list(self, hass: HomeAssistant, prefix: str) -> list[IconListItem]:
        if self.cache:
            return self.cache

        icon_path = hass.config.path(ICON_PATH)

        loop = asyncio.get_running_loop()

        icons = await loop.run_in_executor(None, list_icons, icon_path)

        self.cache.extend(icons)

        return self.cache

    async def icon(
        self, hass: HomeAssistant, prefix: str, icon: str
    ) -> IconData | None:

        icon_root = hass.config.path(ICON_PATH)
        icon_path = resolve_icon_path(icon_root, icon)

        loop = asyncio.get_running_loop()
        svg = await loop.run_in_executor(None, read_icon, icon_path)

        icon_dir = os.path.dirname(icon_path)
        if icon_dir not in self.profile_cache:
            try:
                profile, profile_path = await loop.run_in_executor(
                    None, find_svg_profile, icon_path, icon_root
                )
                self.profile_cache[icon_dir] = profile
                if profile_path:
                    LOGGER.debug("Using SVG profile %s for %s", profile_path, icon_dir)
            except (OSError, ValueError, SvgProfileError) as err:
                LOGGER.warning("Ignoring invalid SVG profile for %s: %s", icon, err)
                self.profile_cache[icon_dir] = None

        return process_svg(svg, profile=self.profile_cache[icon_dir])
