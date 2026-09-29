from pathlib import Path
from xml.etree import ElementTree as ET


SPOT = Path(__file__).parent / "custom_icons" / "ko-liquid-pilot" / "spot.svg"


def test_liquid_glass_spot_is_valid_svg():
    root = ET.parse(SPOT).getroot()
    assert root.attrib["viewBox"] == "0 0 64 64"


def test_liquid_glass_spot_has_dynamic_and_fixed_layers():
    text = SPOT.read_text(encoding="utf-8")
    assert text.count("currentColor") >= 4
    assert "#05070A" in text
    assert "#FFFFFF" in text
    assert "stop-opacity" in text
    assert 'fill="currentColor"' in text


def test_liquid_glass_spot_keeps_canvas_transparent():
    text = SPOT.read_text(encoding="utf-8")
    assert "<rect" not in text
    assert 'fill="#FFFFFF"' not in text.split("<defs>", 1)[0]
