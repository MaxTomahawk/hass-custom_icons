![example image](https://github.com/user-attachments/assets/de32cf37-4564-420e-b6c8-917cc97aa108)

> This fork is based on Thomas Lovén's `hass-custom_icons` (MIT). It keeps upstream Custom Icons behavior and adds maintained local-SVG profile support, including directory-level duotone rendering, plus a build-sync check for the frontend loader.

## Installation

- Add/install this repository through HACS as `MaxTomahawk/hass-custom_icons` [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MaxTomahawk&repository=hass-custom_icons)
- Restart Home Assistant
- Click this [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=custom_icons)
  - Alternatively, go to your integrations configuration, click "Add Integration" and find "Custom Icons"

## Usage

- Go to your integrations configuration, click "Custom Icons" and then "CONFIGURE".

![configuration](https://github.com/user-attachments/assets/3e88a032-0fb1-4975-95e6-07a809cd2239)

- Here, in the Configuration Panel, you can pick which icon sets you want to use.
  If you don't see any icons, make sure to click "Download" to update Iconify icons once.

![select sets](https://github.com/user-attachments/assets/84c3289c-ec4b-40c8-b54d-be4f2f1dd89d)

- After enabling icon sets and refreshing your browser (F5) you will be able to find your icons in the icon picker.

![icon picker](https://github.com/user-attachments/assets/fb17667e-8161-48a8-adc9-78893961dd05)

## Icon sets

### Your own icons

To use your own icons, place their `.svg` files in `<config>/custom_icons` (the directory should have been created by Custom Icons automatically).
You can also place icons in subdirectories.

If you add new icons or change a local profile, push the **RELOAD** button before testing the result.

Make sure the "Local" collection is enabled, and the icons will then be available using the `local:` prefix.

#### Directory-level SVG profiles

A local icon directory can contain an `_iconset.json` file. The profile is inherited by nested directories until another `_iconset.json` overrides it. The profile changes rendering at load time; individual SVG files do not need to contain duplicated palette rules.

For duotone rendering, place this next to the icons, for example `<config>/custom_icons/dt/_iconset.json`:

```json
{
  "profile": "duotone"
}
```

The default duotone profile recognizes `primary`/`secondary` roles through IDs such as `primary`, `primary-2`, `secondary`, and `secondary-2`; `data-name="primary|secondary"`; and the `primary`, `secondary`, `fa-primary`, and `fa-secondary` classes. It also applies to non-path SVG geometry such as circles, rectangles, polygons, and groups.

The default palette is derived from the icon's inherited `currentcolor`:

```text
primary:   oklch(from currentcolor 0.7485 min(c,0.1258) h / 1)
secondary: oklch(from currentcolor 0.8794 min(c,0.0505) h / 1)
```

Role elements with the generated default fill/opacity (or no explicit presentation value) inherit the directory profile. Explicit non-standard fill or opacity values are treated as per-icon exceptions and remain untouched, so hand-tuned icons are not flattened by the profile.

The profile can be customized without editing the SVG files:

```json
{
  "profile": "duotone",
  "primary_color": "currentcolor",
  "secondary_color": "color-mix(in oklch, currentcolor 45%, white)",
  "primary_opacity": "1",
  "secondary_opacity": "0.85"
}
```

The resulting SVG also exposes these CSS custom-property overrides to Home Assistant themes/cards:

- `--custom-icons-duotone-primary-color`
- `--custom-icons-duotone-secondary-color`
- `--custom-icons-duotone-primary-opacity`
- `--custom-icons-duotone-secondary-opacity`

For compatibility with existing customized SVGs, the default primary opacity falls back to `--primary-svg-opacity` and then `1`.

> **Note about safety:**
>
> SVG files may contain SVG and Javascript and shall be considered unsafe.
> Home Assistant normally protects you from harmful code in SVG icons, but in order to make e.g. full color or animated icons work this protection has been removed by Custom Icons.
>
> Only use icons you trust (and preferably have inspected the code for). This fork does not add a sanitizer to upstream Custom Icons' full-SVG rendering path.

> **Note about colors:**
>
> SVG files can contain color information.
> Some SVGs are meant to be used as icons, and will have no color or the magic `currentcolor` value. Those will follow the color of your entities (e.g. turning yellow when an entity is switched on or adjusting to a light color).
> Some SVGs are _not_ meant to be used as icons, they can include elements of one or more colors.
>
> For a reusable duotone collection, prefer a directory-level profile over repeating color rules in every SVG. For other colorized files, the upstream `currentcolor` approach remains available.

### Iconify

[Iconify](https://iconify.design/) is a framework for several popular icon sets.

The icon sets are updated frequently, so you can manually download the latest updates from the Custom Icons configuration panel.

You also need to download them by clicking the button manually the first time.

### Fontawesome Pro icons

If you bought the fontawesome package, you should have received the icon set as a zip file or something.

Somewhere in this file, there's a folder named `metadata` which contains a file `icons.json`.

Copy and rename this file to `<config>/custom_icons/fontawesome.json`.

Push the RELOAD button in the Custom Icons configuration panel.

### Webfonts

There is some support for svg webfonts like [RPG Awesome](https://github.com/nagoshiashumari/Rpg-Awesome/).

To use those, get the `<whatever>-webfont.svg` file and copy that to `<config>/custom_icons/`.

Push the RELOAD button in the Custom Icons configuration panel.

Note that SVG webfonts has been deprecated and removed from the SVG standard. Things may or may not work.

## Development

`js/loader/main.ts` and `js/panel/main.ts` are the sources for the committed frontend bundles. CI rebuilds both bundles and fails if `custom_components/custom_icons/loader.js` or `panel.js` is stale. This prevents source fixes from being merged without the artifact that Home Assistant actually serves.

## FAQ

### Does this replace `hass-fontawesome`?

Yes

### How do I migrate?

- Remove `hass-fontawesome`
- Install `hass-custom_icons`
- Open the Custom Icons configuration panel (see [Usage](#usage) above)
- Click "Download"

### Do I need all that `#fullcolor` nonsense from `hass-fontawesome`?

No
