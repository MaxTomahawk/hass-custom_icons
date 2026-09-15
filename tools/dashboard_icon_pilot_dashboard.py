#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def pilot_button(name: str, icon: str, subtitle: str) -> dict:
    return {
        "type": "custom:button-card",
        "name": name,
        "label": subtitle,
        "icon": icon,
        "show_label": True,
        "show_state": False,
        "tap_action": {"action": "none"},
        "hold_action": {"action": "none"},
        "styles": {
            "card": [
                {"height": "118px"},
                {"padding": "12px"},
                {"border-radius": "18px"},
            ],
            "icon": [
                {"width": "52px"},
                {"height": "52px"},
                {"color": "var(--primary-color)"},
            ],
            "name": [
                {"font-size": "14px"},
                {"font-weight": "600"},
            ],
            "label": [
                {"font-size": "11px"},
                {"opacity": "0.72"},
            ],
        },
    }


def build_dashboard(manifest: list[dict]) -> dict:
    cards: list[dict] = [
        {
            "type": "markdown",
            "content": (
                "# Icon Pilot\n"
                "Tien iconen uit het echte Overview-dashboard, telkens **origineel / "
                "duotone / glow**. De pilot verandert het bestaande dashboard niet."
            ),
        }
    ]

    for item in manifest:
        cards.append(
            {
                "type": "vertical-stack",
                "cards": [
                    {"type": "markdown", "content": f"### `{item['original']}`"},
                    {
                        "type": "horizontal-stack",
                        "cards": [
                            pilot_button("Origineel", item["original"], item["kind"].upper()),
                            pilot_button("Duotone", item["duotone"], "PILOT"),
                            pilot_button("Glow", item["glow"], "PILOT"),
                        ],
                    },
                ],
            }
        )

    return {
        "version": 1,
        "minor_version": 1,
        "key": "lovelace.dashboard_icon_pilot",
        "data": {
            "config": {
                "views": [
                    {
                        "title": "Icon Pilot",
                        "path": "pilot",
                        "icon": "local:pilot-glow/mdi-home-roof",
                        "type": "masonry",
                        "cards": cards,
                    }
                ]
            }
        },
    }


def build_dashboard_item() -> dict:
    return {
        "id": "dashboard_icon_pilot",
        "show_in_sidebar": True,
        "icon": "local:pilot-glow/mdi-home-roof",
        "title": "Icon Pilot",
        "require_admin": True,
        "mode": "storage",
        "url_path": "icon-pilot",
    }


def validate(dashboard: dict, dashboard_item: dict) -> dict:
    errors: list[str] = []
    try:
        view = dashboard["data"]["config"]["views"][0]
        stacks = [card for card in view["cards"] if card.get("type") == "vertical-stack"]
        buttons = [
            button
            for stack in stacks
            for child in stack["cards"]
            if child.get("type") == "horizontal-stack"
            for button in child["cards"]
        ]
        if len(stacks) != 10 or len(buttons) != 30:
            errors.append(
                f"expected 10 comparison rows / 30 buttons, got {len(stacks)} / {len(buttons)}"
            )
        if dashboard.get("key") != "lovelace.dashboard_icon_pilot":
            errors.append("unexpected dashboard storage key")
        if dashboard_item.get("id") != "dashboard_icon_pilot":
            errors.append("unexpected dashboard registry id")
        if dashboard_item.get("require_admin") is not True:
            errors.append("pilot dashboard must remain admin-only")
    except (KeyError, IndexError, TypeError) as err:
        errors.append(f"invalid dashboard structure: {err}")

    return {"ok": not errors, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot-output", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = args.pilot_output / "pilot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest) != 10:
        raise SystemExit(f"expected 10 pilot icons, got {len(manifest)}")

    dashboard = build_dashboard(manifest)
    dashboard_item = build_dashboard_item()
    proof = validate(dashboard, dashboard_item)

    (args.pilot_output / "lovelace.dashboard_icon_pilot").write_text(
        json.dumps(dashboard, indent=2) + "\n", encoding="utf-8"
    )
    (args.pilot_output / "dashboard_item.json").write_text(
        json.dumps(dashboard_item, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps({"dashboard": dashboard_item, "validation": proof}, indent=2))
    if not proof["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
