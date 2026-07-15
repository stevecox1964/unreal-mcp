from __future__ import annotations

import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


CARDINAL_DIRECTIONS = ("N", "S", "E", "W")
_PANEL_SIZE = (640, 360)
_HEADER_HEIGHT = 64


def _heading_font(size: int = 46):
    """Return a large bold font, with Pillow's bundled default as fallback."""
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def build_place_composite(views: dict[str, str | Path], output_path: str | Path) -> Path:
    """Render one durable N/S/E/W place image.

    ``views`` must contain exactly the four cardinal directions. Each panel has
    a black header and large white direction text; grid/world coordinates are
    deliberately absent from the pixels. Example valid input::

        build_place_composite(
            {"N": "north.png", "S": "south.png", "E": "east.png", "W": "west.png"},
            "place_images/abc123.png",
        )
    """
    normalized = {str(k).upper(): Path(v) for k, v in views.items()}
    missing = [d for d in CARDINAL_DIRECTIONS if d not in normalized]
    extras = sorted(set(normalized) - set(CARDINAL_DIRECTIONS))
    if missing or extras:
        raise ValueError(f"place image requires exactly N/S/E/W; missing={missing}, extras={extras}")
    for direction, path in normalized.items():
        if not path.is_file():
            raise FileNotFoundError(f"{direction} place view not found: {path}")

    panel_w, image_h = _PANEL_SIZE
    panel_h = image_h + _HEADER_HEIGHT
    composite = Image.new("RGB", (panel_w * 2, panel_h * 2), "black")
    font = _heading_font()
    positions = {"N": (0, 0), "S": (panel_w, 0), "E": (0, panel_h), "W": (panel_w, panel_h)}

    for direction in CARDINAL_DIRECTIONS:
        x, y = positions[direction]
        with Image.open(normalized[direction]) as source:
            frame = ImageOps.fit(source.convert("RGB"), _PANEL_SIZE, method=Image.Resampling.LANCZOS)
        panel = Image.new("RGB", (panel_w, panel_h), "black")
        panel.paste(frame, (0, _HEADER_HEIGHT))
        draw = ImageDraw.Draw(panel)
        box = draw.textbbox((0, 0), direction, font=font)
        text_w = box[2] - box[0]
        text_h = box[3] - box[1]
        draw.text(((panel_w - text_w) / 2, (_HEADER_HEIGHT - text_h) / 2 - box[1]),
                  direction, fill="white", font=font)
        composite.paste(panel, (x, y))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp.png")
    composite.save(temporary, format="PNG", optimize=True)
    os.replace(temporary, output)
    return output


def expose_in_agent_history(shared_image: str | Path, observations_dir: str | Path,
                            place_image_id: str) -> Path:
    """Expose a shared place image in an APC's observations/place_history folder.

    A hard link avoids duplicating the shared pixels. Filesystems that cannot
    hard-link fall back to a copy so the visual history remains inspectable.
    Example valid input::

        expose_in_agent_history("places/images/abc.png", "agents/maren/observations", "abc")
    """
    source = Path(shared_image)
    if not source.is_file():
        raise FileNotFoundError(f"shared place image not found: {source}")
    history_dir = Path(observations_dir) / "place_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    destination = history_dir / f"{place_image_id}.png"
    if destination.exists():
        return destination
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
    return destination
