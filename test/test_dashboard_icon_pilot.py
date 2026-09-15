import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).parents[1]


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = load_module("dashboard_icon_pilot", ROOT / "tools" / "dashboard_icon_pilot.py")
pilot_dashboard = load_module(
    "dashboard_icon_pilot_dashboard", ROOT / "tools" / "dashboard_icon_pilot_dashboard.py"
)


class DashboardIconPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.custom_icons = self.root / "custom_icons"
        dt = self.custom_icons / "dt"
        dt.mkdir(parents=True)

        fixture = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            '<path id="secondary" d="M4 4h16v16H4z"/>'
            '<path id="primary" d="M8 8h8v8H8z"/>'
            '</svg>'
        )
        for name in ("floor-lamp", "bedroom-7", "monitor", "desk-lamp-round-left"):
            (dt / f"{name}.svg").write_text(fixture, encoding="utf-8")

        self.hue_js = self.root / "hue.js"
        self.hue_js.write_text(
            'const icons={"bulb-group-ceiling-round":{path:"M2 2h20v20H2z"},'
            '"play-bar":{path:"M3 12h18v3H3z"}};',
            encoding="utf-8",
        )
        self.output = self.root / "output"

    def tearDown(self):
        self.temp.cleanup()

    def test_builds_two_packs_and_comparison_dashboard(self):
        built = pilot.build(self.custom_icons, self.hue_js, self.output)
        icon_proof = pilot.validate(self.output)
        manifest = json.loads((self.output / "pilot_manifest.json").read_text())

        dashboard = pilot_dashboard.build_dashboard(manifest)
        dashboard_item = pilot_dashboard.build_dashboard_item()
        dashboard_proof = pilot_dashboard.validate(dashboard, dashboard_item)

        self.assertEqual(10, built["icons"])
        self.assertEqual(20, built["files"])
        self.assertTrue(icon_proof["ok"], icon_proof["errors"])
        self.assertTrue(dashboard_proof["ok"], dashboard_proof["errors"])
        self.assertEqual("local:pilot-duotone/mdi-water", manifest[0]["duotone"])
        self.assertEqual("local:pilot-gradient/mdi-water", manifest[0]["gradient"])
        self.assertTrue(dashboard_item["require_admin"])
        self.assertEqual("OneUI 8.5 Frosted Green", dashboard["data"]["config"]["views"][0]["theme"])

        dashboard_with_preview = pilot_dashboard.build_dashboard(manifest, "light.example")
        preview_cards = dashboard_with_preview["data"]["config"]["views"][0]["cards"]
        native_tiles = []
        for card in preview_cards:
            if card.get("type") == "horizontal-stack":
                native_tiles.extend(c for c in card.get("cards", []) if c.get("type") == "tile")
        self.assertEqual(2, len(native_tiles))
        self.assertEqual("light.example", native_tiles[0]["entity"])
        self.assertEqual("local:pilot-gradient/hue-ceiling-round", native_tiles[1]["icon"])

        for svg in (self.output / "pilot-gradient").glob("*.svg"):
            text = svg.read_text(encoding="utf-8").lower()
            self.assertIn("pilot-gradient", text)
            self.assertNotIn("<filter", text)
            self.assertNotIn("fegaussianblur", text)
            self.assertNotIn("pilot-glow", text)

    def test_generated_svg_has_no_external_or_script_content(self):
        pilot.build(self.custom_icons, self.hue_js, self.output)
        for svg in self.output.rglob("*.svg"):
            text = svg.read_text(encoding="utf-8").lower()
            self.assertNotIn("<script", text)
            self.assertNotIn("href=\"http", text)
            self.assertNotIn("href='http", text)


if __name__ == "__main__":
    unittest.main()
