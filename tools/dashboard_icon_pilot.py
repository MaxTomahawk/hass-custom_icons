#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ET.register_namespace('', 'http://www.w3.org/2000/svg')
SVG_NS = 'http://www.w3.org/2000/svg'
Q = lambda tag: f'{{{SVG_NS}}}{tag}'

MDI_PATHS = {
    'mdi-water': 'M12,20A6,6 0 0,1 6,14C6,10 12,3.25 12,3.25C12,3.25 18,10 18,14A6,6 0 0,1 12,20Z',
    'mdi-lightbulb-off': 'M12,2C9.76,2 7.78,3.05 6.5,4.68L16.31,14.5C17.94,13.21 19,11.24 19,9A7,7 0 0,0 12,2M3.28,4L2,5.27L5.04,8.3C5,8.53 5,8.76 5,9C5,11.38 6.19,13.47 8,14.74V17A1,1 0 0,0 9,18H14.73L18.73,22L20,20.72L3.28,4M9,20V21A1,1 0 0,0 10,22H14A1,1 0 0,0 15,21V20H9Z',
    'mdi-lamps-outline': 'M8.5 4L9.35 7H4.65L5.5 4H8.5M10 2H4L2 9H12L10 2M6 10H8V20H11V22H3V20H6V10M18.5 10L19.35 13H14.65L15.5 10H18.5M20 8H14L12 15H22L20 8M16 16H18V20H21V22H13V20H16V16Z',
    'mdi-home-roof': 'M19 16H22L12 7L2 16H5L12 9.69L19 16M7 8.81V7H4V11.5L7 8.81Z',
}

SELECTION = [
    {'name': 'mdi-water', 'original': 'mdi:water', 'kind': 'mdi'},
    {'name': 'mdi-lightbulb-off', 'original': 'mdi:lightbulb-off', 'kind': 'mdi'},
    {'name': 'mdi-lamps-outline', 'original': 'mdi:lamps-outline', 'kind': 'mdi'},
    {'name': 'mdi-home-roof', 'original': 'mdi:home-roof', 'kind': 'mdi'},
    {'name': 'hue-ceiling-round', 'original': 'hue:bulb-group-ceiling-round', 'kind': 'hue', 'source': 'bulb-group-ceiling-round'},
    {'name': 'hue-play-bar', 'original': 'hue:play-bar', 'kind': 'hue', 'source': 'play-bar'},
    {'name': 'dt-floor-lamp', 'original': 'local:dt/floor-lamp', 'kind': 'local', 'source': 'floor-lamp'},
    {'name': 'dt-bedroom-7', 'original': 'local:dt/bedroom-7', 'kind': 'local', 'source': 'bedroom-7'},
    {'name': 'dt-monitor', 'original': 'local:dt/monitor', 'kind': 'local', 'source': 'monitor'},
    {'name': 'dt-desk-lamp-round-left', 'original': 'local:dt/desk-lamp-round-left', 'kind': 'local', 'source': 'desk-lamp-round-left'},
]

DUOTONE_PROFILE = {
    'profile': 'duotone',
    'primary_color': 'oklch(from currentcolor 0.72 min(c,0.145) h / 1)',
    'secondary_color': 'oklch(from currentcolor 0.90 min(c,0.055) h / 1)',
    'primary_opacity': '1',
    'secondary_opacity': '1',
}

GRADIENT_STYLE = r'''
.pilot-gradient-base, .pilot-gradient-base * {
  fill: url(#pilot-gradient) !important;
  stroke: none !important;
}
'''.strip()

PRESENTATION_ATTRS = {
    'fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-opacity',
    'opacity', 'style', 'color', 'filter', 'clip-path', 'mask',
}

ROLE_CLASSES = {'primary', 'secondary', 'fa-primary', 'fa-secondary'}


def parse_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.attrib.get('viewBox', '0 0 24 24').replace(',', ' ').split()
    if len(raw) != 4:
        return (0.0, 0.0, 24.0, 24.0)
    return tuple(float(x) for x in raw)  # type: ignore[return-value]


def role_of(el: ET.Element) -> str | None:
    classes = set(el.attrib.get('class', '').split())
    if classes & {'secondary', 'fa-secondary'}:
        return 'secondary'
    if classes & {'primary', 'fa-primary'}:
        return 'primary'
    ident = el.attrib.get('id', '').lower()
    data_name = el.attrib.get('data-name', '').lower()
    if ident == 'secondary' or ident.startswith('secondary-') or data_name == 'secondary':
        return 'secondary'
    if ident == 'primary' or ident.startswith('primary-') or data_name == 'primary':
        return 'primary'
    return None


def sanitize_tree(el: ET.Element, preserve_roles: bool) -> ET.Element:
    out = copy.deepcopy(el)
    for node in out.iter():
        role = role_of(node) if preserve_roles else None
        for attr in list(node.attrib):
            local = attr.split('}', 1)[-1]
            if local in PRESENTATION_ATTRS:
                node.attrib.pop(attr, None)
        if preserve_roles and role:
            node.set('id', role)
            node.attrib.pop('data-name', None)
            node.set('class', role)
        else:
            node.attrib.pop('id', None)
            node.attrib.pop('data-name', None)
            if 'class' in node.attrib:
                keep = [c for c in node.attrib['class'].split() if c not in ROLE_CLASSES]
                if keep:
                    node.attrib['class'] = ' '.join(keep)
                else:
                    node.attrib.pop('class', None)
    return out


def geometry_children(root: ET.Element) -> list[ET.Element]:
    keep = []
    for child in list(root):
        tag = child.tag.split('}', 1)[-1]
        if tag in {'defs', 'style', 'title', 'desc', 'metadata'}:
            continue
        keep.append(child)
    return keep


def source_from_mdi(name: str) -> ET.Element:
    svg = ET.Element(Q('svg'), {'viewBox': '0 0 24 24', 'data-pilot-source': name})
    ET.SubElement(svg, Q('path'), {'d': MDI_PATHS[name]})
    return svg


def extract_hue_path(js_text: str, icon_name: str) -> str:
    pattern = re.compile(r'"' + re.escape(icon_name) + r'"\s*:\s*\{\s*path\s*:\s*"([^"]+)"', re.S)
    match = pattern.search(js_text)
    if not match:
        raise ValueError(f'Hue icon not found: {icon_name}')
    return match.group(1).replace('\\"', '"')


def source_from_hue(js_text: str, name: str) -> ET.Element:
    svg = ET.Element(Q('svg'), {'viewBox': '0 0 24 24', 'data-pilot-source': f'hue:{name}'})
    ET.SubElement(svg, Q('path'), {'d': extract_hue_path(js_text, name)})
    return svg


def source_from_local(root: Path, name: str) -> ET.Element:
    path = root / 'dt' / f'{name}.svg'
    return ET.fromstring(path.read_text(encoding='utf-8'))


def build_duotone(source: ET.Element, source_ref: str) -> ET.Element:
    vb = parse_viewbox(source)
    x, y, w, h = vb
    cx, cy = x + w / 2, y + h / 2
    out = ET.Element(Q('svg'), {
        'viewBox': f'{x:g} {y:g} {w:g} {h:g}',
        'data-pilot-source': source_ref,
        'data-pilot-style': 'duotone',
    })
    children = geometry_children(source)
    role_children = [(child, role_of(child)) for child in children]
    has_roles = any(role for _, role in role_children)
    if has_roles:
        for child, _ in role_children:
            out.append(sanitize_tree(child, preserve_roles=True))
    else:
        secondary = ET.SubElement(out, Q('g'), {
            'id': 'secondary',
            'class': 'secondary',
            'transform': f'translate({cx:g} {cy:g}) scale(1.045) translate({-cx:g} {-cy:g})',
        })
        primary = ET.SubElement(out, Q('g'), {'id': 'primary', 'class': 'primary'})
        for child in children:
            secondary.append(sanitize_tree(child, preserve_roles=False))
            primary.append(sanitize_tree(child, preserve_roles=False))
    return out


def build_gradient(source: ET.Element, source_ref: str) -> ET.Element:
    vb = parse_viewbox(source)
    x, y, w, h = vb
    out = ET.Element(Q('svg'), {
        'viewBox': f'{x:g} {y:g} {w:g} {h:g}',
        'data-pilot-source': source_ref,
        'data-pilot-style': 'gradient',
    })
    defs = ET.SubElement(out, Q('defs'))
    gradient = ET.SubElement(defs, Q('linearGradient'), {
        'id': 'pilot-gradient', 'x1': '0%', 'y1': '0%', 'x2': '100%', 'y2': '100%'
    })
    ET.SubElement(gradient, Q('stop'), {
        'offset': '0%', 'style': 'stop-color:oklch(from currentcolor 0.96 min(c,0.045) h / 1)'
    })
    ET.SubElement(gradient, Q('stop'), {
        'offset': '42%', 'style': 'stop-color:oklch(from currentcolor 0.80 min(c,0.13) h / 1)'
    })
    ET.SubElement(gradient, Q('stop'), {
        'offset': '100%', 'style': 'stop-color:oklch(from currentcolor 0.61 min(c,0.17) h / 1)'
    })
    style = ET.SubElement(defs, Q('style'))
    style.text = GRADIENT_STYLE

    base = ET.SubElement(out, Q('g'), {'class': 'pilot-gradient-base'})
    for child in geometry_children(source):
        base.append(sanitize_tree(child, preserve_roles=False))
    return out

def write_svg(root: ET.Element, path: Path) -> None:
    ET.indent(root, space='  ')
    path.write_text('<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n', encoding='utf-8')


def build(custom_icons_root: Path, hue_js: Path, output: Path) -> dict:
    if output.exists():
        shutil.rmtree(output)
    duo_dir = output / 'pilot-duotone'
    gradient_dir = output / 'pilot-gradient'
    duo_dir.mkdir(parents=True)
    gradient_dir.mkdir(parents=True)
    (duo_dir / '_iconset.json').write_text(json.dumps(DUOTONE_PROFILE, indent=2) + '\n', encoding='utf-8')
    hue_text = hue_js.read_text(encoding='utf-8')
    manifest = []
    for item in SELECTION:
        if item['kind'] == 'mdi':
            source = source_from_mdi(item['name'])
        elif item['kind'] == 'hue':
            source = source_from_hue(hue_text, item['source'])
        else:
            source = source_from_local(custom_icons_root, item['source'])
        write_svg(build_duotone(source, item['original']), duo_dir / f"{item['name']}.svg")
        write_svg(build_gradient(source, item['original']), gradient_dir / f"{item['name']}.svg")
        manifest.append({
            **item,
            'duotone': f"local:pilot-duotone/{item['name']}",
            'gradient': f"local:pilot-gradient/{item['name']}",
        })
    (output / 'pilot_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return {'icons': len(manifest), 'files': len(list(output.rglob('*.svg'))), 'manifest': manifest}


def validate(output: Path) -> dict:
    errors = []
    duos = list((output / 'pilot-duotone').glob('*.svg'))
    gradients = list((output / 'pilot-gradient').glob('*.svg'))
    for path in duos + gradients:
        try:
            root = ET.fromstring(path.read_text(encoding='utf-8'))
        except Exception as exc:
            errors.append(f'{path.name}: XML: {exc}')
            continue
        text = path.read_text(encoding='utf-8').lower()
        if '<script' in text or re.search(r'(?:href|xlink:href)\s*=\s*["\']https?://', text):
            errors.append(f'{path.name}: unsafe external/script content')
        if path.parent.name == 'pilot-duotone':
            if not any(role_of(el) in {'primary', 'secondary'} for el in root.iter()):
                errors.append(f'{path.name}: no duotone roles')
        else:
            for required in ('pilot-gradient', 'pilot-gradient-base'):
                if required not in text:
                    errors.append(f'{path.name}: missing {required}')
            for forbidden in ('<filter', 'fegaussianblur', 'feflood', 'fecomposite', 'femerge', 'pilot-glow', 'pilot-soft-glow'):
                if forbidden in text:
                    errors.append(f'{path.name}: unexpected glow effect {forbidden}')
    if len(duos) != 10 or len(gradients) != 10:
        errors.append(f'expected 10+10 SVGs, got {len(duos)}+{len(gradients)}')
    return {'ok': not errors, 'errors': errors, 'duotone': len(duos), 'gradient': len(gradients)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--custom-icons-root', type=Path, required=True)
    ap.add_argument('--hue-js', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = build(args.custom_icons_root, args.hue_js, args.output)
    proof = validate(args.output)
    print(json.dumps({'build': result, 'validation': proof}, indent=2))
    if not proof['ok']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
