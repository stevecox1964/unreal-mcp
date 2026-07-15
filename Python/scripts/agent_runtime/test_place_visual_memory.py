"""Offline checks for durable four-view place images and APC visual history."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime.place_db import PlaceDB  # noqa: E402
from agent_runtime.place_visuals import (  # noqa: E402
    build_place_composite,
    expose_in_agent_history,
)


def check(label, condition):
    if not condition:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def _source_views(root: Path) -> dict[str, Path]:
    colors = {"N": "red", "S": "green", "E": "blue", "W": "orange"}
    views = {}
    for direction, color in colors.items():
        path = root / "sources" / f"{direction}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (160, 90), color).save(path)
        views[direction] = path
    return views


def main():
    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp) / "World"
        db = PlaceDB(world / "world_places.db")
        views = _source_views(world)
        composite = world / "places" / "images" / "community.png"
        build_place_composite(views, composite)

        with Image.open(composite) as image:
            check("composite is a stable 2x2 panel", image.size == (1280, 848))
            header = image.crop((0, 0, 640, 64)).convert("L")
            lo, hi = header.getextrema()
            check("header contains black background and white heading", lo == 0 and hi == 255)

        rel_views = {d: str(p.relative_to(world)) for d, p in views.items()}
        db.set_name("dufus", 2, 3, "Coffee Shop", "Day 1, 09:00")
        community = db.record_place_image(
            "dufus", 2, 3, str(composite.relative_to(world)), rel_views,
            description="N: storefront\nS: tables\nE: road\nW: alley",
        )
        current = db.current_place_image("dufus", 2, 3)
        check("community PlaceDB row resolves its image id",
              current and current["place_image_id"] == community["place_image_id"])
        place = db.get_place(2, 3)
        check("place query returns image id and scene description",
              place["place_image_id"] == community["place_image_id"]
              and "storefront" in place["description"])
        check("place visual ids and paths have no sim-run number",
              "SR" not in community["place_image_id"] and "SR" not in community["image_path"])

        history_file = expose_in_agent_history(
            composite, world / "agents" / "dufus" / "observations",
            community["place_image_id"],
        )
        check("capturing APC can inspect its visual history", history_file.is_file())

        linked = db.link_agent_to_place_image("maren", community["place_image_id"])
        maren_history = expose_in_agent_history(
            db.absolute_image_path(linked), world / "agents" / "maren" / "observations",
            linked["place_image_id"],
        )
        check("another APC reuses the shared image in its own history", maren_history.is_file())
        check("APC history query returns the exact revision",
              db.agent_visual_history("maren")[0]["place_image_id"]
              == community["place_image_id"])

        db.add_owned_place("maren", 2, 3, "My Booth", 10.0, -20.0)
        owned_composite = world / "places" / "images" / "owned.png"
        build_place_composite(views, owned_composite)
        owned = db.record_place_image(
            "maren", 2, 3, str(owned_composite.relative_to(world)), rel_views,
            description="Maren's booth", place_name="My Booth",
        )
        check("owned place has an independent visual-memory id",
              owned["place_kind"] == "owned"
              and owned["place_image_id"] != community["place_image_id"])
        check("owned place resolves by semantic name",
              db.current_place_image("maren", 2, 3, "My Booth")["place_image_id"]
              == owned["place_image_id"])

        removed = db.reset()
        check("reset reports visual rows", removed["place_images"] == 2
              and removed["agent_visual_history"] == 3)
        check("full PlaceDB reset deletes shared images",
              not composite.exists() and not owned_composite.exists())
        check("full PlaceDB reset deletes per-APC history links",
              not history_file.exists() and not maren_history.exists())

    print("\nAll place-visual-memory checks passed.")


if __name__ == "__main__":
    main()
