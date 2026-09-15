import importlib.util
import json
import pathlib
import tempfile
import unittest

MODULE_PATH = (
    pathlib.Path(__file__).parents[1]
    / "custom_components"
    / "custom_icons"
    / "svg_profiles.py"
)
spec = importlib.util.spec_from_file_location("svg_profiles", MODULE_PATH)
svg_profiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(svg_profiles)


class SvgProfileTests(unittest.TestCase):
    def test_default_duotone_css_matches_current_palette(self):
        profile = svg_profiles.normalize_svg_profile({"profile": "duotone"})
        css = svg_profiles.build_svg_profile_css(profile)

        self.assertIn("0.7485 min(c,0.1258)", css)
        self.assertIn("0.8794 min(c,0.0505)", css)
        self.assertIn("--primary-svg-opacity, 1", css)
        self.assertIn('[id^="secondary-"]', css)
        self.assertIn('[data-name="primary"]', css)
        self.assertIn(".fa-secondary", css)

    def test_opacity_is_applied_to_role_not_descendants(self):
        profile = svg_profiles.normalize_svg_profile({"profile": "duotone"})
        css = svg_profiles.build_svg_profile_css(profile)

        primary_opacity_rule = css.split("--custom-icons-duotone-primary-opacity", 1)[0]
        primary_opacity_selectors = primary_opacity_rule.rsplit("}", 1)[-1]
        self.assertIn("#primary", primary_opacity_selectors)
        self.assertNotIn("#primary *", primary_opacity_selectors)

    def test_duotone_profile_supports_safe_overrides(self):
        profile = svg_profiles.normalize_svg_profile(
            {
                "profile": "duotone",
                "primary_color": "currentcolor",
                "secondary_color": "color-mix(in oklch, currentcolor 40%, white)",
                "primary_opacity": "0.8",
                "secondary_opacity": "0.6",
            }
        )
        css = svg_profiles.build_svg_profile_css(profile)

        self.assertIn("currentcolor", css)
        self.assertIn("color-mix(in oklch, currentcolor 40%, white)", css)
        self.assertIn("0.8", css)
        self.assertIn("0.6", css)

    def test_unsafe_css_override_is_rejected(self):
        for value in ("red;</style>", "url(https://example.test/icon.svg)"):
            with self.subTest(value=value), self.assertRaises(svg_profiles.SvgProfileError):
                svg_profiles.normalize_svg_profile(
                    {"profile": "duotone", "primary_color": value}
                )

    def test_nearest_profile_is_inherited(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            icon_dir = root / "dt" / "nested"
            icon_dir.mkdir(parents=True)
            icon = icon_dir / "lamp.svg"
            icon.write_text("<svg viewBox='0 0 24 24'></svg>", encoding="utf-8")
            (root / "dt" / svg_profiles.PROFILE_FILENAME).write_text(
                json.dumps({"profile": "duotone"}), encoding="utf-8"
            )

            profile, profile_path = svg_profiles.find_svg_profile(str(icon), str(root))

            self.assertEqual("duotone", profile["profile"])
            self.assertEqual(
                str(root / "dt" / svg_profiles.PROFILE_FILENAME), profile_path
            )

    def test_no_profile_returns_none(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            icon = root / "plain.svg"
            icon.write_text("<svg viewBox='0 0 24 24'></svg>", encoding="utf-8")

            profile, profile_path = svg_profiles.find_svg_profile(str(icon), str(root))

            self.assertIsNone(profile)
            self.assertIsNone(profile_path)


if __name__ == "__main__":
    unittest.main()
