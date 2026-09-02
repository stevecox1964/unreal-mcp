"""Unreal World Sim — local web UI for managing agents under Python/worlds/."""

import json
import re
from pathlib import Path
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agent_runtime import agenda, places_manifest
from agent_runtime.landmarks import merge_entries, scan_landmarks
from agent_runtime.config_store import read_config, write_config, is_secret, setup_status
from agent_runtime.map_capture import (MAP_CAMERA_ACTOR, MAP_CAMERA_ROTATION,
                                       MAP_CAPTURE_ASPECT, MAP_CAPTURE_MARGIN,
                                       camera_pose_for_bounds)
from agent_runtime import provider_profiles
from agent_runtime import run_replay
from agent_runtime.runner_client import RunnerClient, DEFAULT_BASE_URL
from agent_runtime.place_db import (COMMUNITY_SURVEY_MAX_AGE_SECONDS,
                                    PLACE_EXTENT_CM, PlaceDB)
from agent_runtime.world_grid import WorldGrid
from web_ui import unreal_client

BASE_DIR = Path(__file__).parent
WORLDS_DIR = BASE_DIR.parent / "worlds"
ENV_PATH = BASE_DIR.parent / ".env"   # provider/model config the settings page manages
CONFIG_PATH = BASE_DIR.parent / "config.json"   # named provider profiles + role assignments
MAP_STALE_SECONDS = COMMUNITY_SURVEY_MAX_AGE_SECONDS

app = FastAPI(title="Unreal World Sim")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/images", StaticFiles(directory=str(BASE_DIR / "images")), name="images")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

DEFAULT_ACTIONS = [
    "idle", "walk_to", "speak_to", "inspect_object",
    "follow_character", "attack", "flee", "observe", "remember",
]

# Shown when an APC has no agenda.json yet, so the editor starts from something
# valid rather than an empty box the author has to guess the schema for (#43).
AGENDA_STARTER = json.dumps({
    "schema_version": agenda.SCHEMA_VERSION,
    "tasks": [{
        "id": "morning_home",
        "start": "07:00",
        "end": "08:30",
        "place": "home",
        "objective": "wake up and get ready for the day",
        "completion": {"type": "time_block_ends"},
    }],
}, indent=2)

# ── Helpers ───────────────────────────────────────────────────────────────────

_PATH_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _path_id(value: str, kind: str) -> str:
    """Validate one user-controlled filesystem identifier without normalizing it."""
    if not isinstance(value, str) or not value or value in (".", "..") or not _PATH_ID_RE.fullmatch(value):
        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    return value


def _contained(root: Path, *parts: str, must_exist: bool = False) -> Path:
    """Resolve a child and prove it remains below its trusted resolved root."""
    root = Path(root).resolve()
    path = root.joinpath(*parts).resolve()
    if path != root and root not in path.parents:
        raise HTTPException(status_code=400, detail="filesystem path escapes its data root")
    if must_exist and not path.exists():
        raise HTTPException(status_code=404, detail="filesystem target not found")
    return path


def _world_dir(level: str, must_exist: bool = True) -> Path:
    return _contained(WORLDS_DIR, _path_id(level, "world"), must_exist=must_exist)


def _world_path(level: str, *parts: str, must_exist: bool = False) -> Path:
    return _contained(_world_dir(level), *parts, must_exist=must_exist)


def _agents_dir(level: str, must_exist: bool = False) -> Path:
    return _world_path(level, "agents", must_exist=must_exist)


def _agent_dir(level: str, agent_id: str, must_exist: bool = False) -> Path:
    return _contained(_agents_dir(level), _path_id(agent_id, "agent"), must_exist=must_exist)


def _agent_path(level: str, agent_id: str, *parts: str, must_exist: bool = False) -> Path:
    return _contained(_agent_dir(level, agent_id, must_exist=True), *parts,
                      must_exist=must_exist)


def _replay_observations(level: str, agent_id: str) -> list[Path]:
    """Return contained replay frames; reject a frame-name symlink escape."""
    obs_dir = _agent_path(level, agent_id, "observations")
    if not obs_dir.exists():
        return []
    frames = []
    for entry in obs_dir.iterdir():
        if run_replay.is_frame_name(entry.name):
            path = _contained(obs_dir, entry.name)
            if path.is_file():
                frames.append(path)
    return frames


def _replay_runs(level: str) -> list[str]:
    """Index frame run tags without following an escaping agent/observations link."""
    runs: set[str] = set()
    for agent_id in list_agents(level):
        for path in _replay_observations(level, agent_id):
            runs.add(path.name.split("_observation_", 1)[0])
    return sorted(runs, key=lambda run: int(run[2:]), reverse=True)

def list_worlds() -> list[str]:
    if not WORLDS_DIR.exists():
        return []
    worlds = []
    for p in WORLDS_DIR.iterdir():
        try:
            if p.is_dir() and _world_dir(p.name) == p.resolve():
                worlds.append(p.name)
        except HTTPException:
            continue
    return sorted(worlds)


def list_agents(level: str) -> list[str]:
    agents_dir = _agents_dir(level)
    if not agents_dir.exists():
        return []
    agents = []
    for p in agents_dir.iterdir():
        try:
            if p.is_dir() and _agent_dir(level, p.name) == p.resolve():
                agents.append(p.name)
        except HTTPException:
            continue
    return sorted(agents)


def load_agent(level: str, agent_id: str) -> dict:
    base = _agent_dir(level, agent_id, must_exist=True)
    state = json.loads(_contained(base, "state.json", must_exist=True).read_text(encoding="utf-8"))
    character = _contained(base, "character.md", must_exist=True).read_text(encoding="utf-8")
    goals = _contained(base, "goals.md", must_exist=True).read_text(encoding="utf-8")
    rules = _contained(base, "rules.md", must_exist=True).read_text(encoding="utf-8")
    tools = json.loads(_contained(base, "tools.json", must_exist=True).read_text(encoding="utf-8"))
    memory_path = _contained(base, "memory.json")
    memory_raw = memory_path.read_text(encoding="utf-8") if memory_path.exists() else "{}"
    agenda_text, agenda_errors = read_agenda(level, agent_id)
    return {
        "state": state,
        "character": character,
        "goals": goals,
        "rules": rules,
        "allowed_actions": "\n".join(tools.get("allowed_actions", DEFAULT_ACTIONS)),
        "agenda_text": agenda_text,
        "agenda_errors": agenda_errors,
        # raw JSON for the viewer panel
        "raw_state": json.dumps(state, indent=2),
        "raw_tools": json.dumps(tools, indent=2),
        "raw_memory": json.dumps(json.loads(memory_raw), indent=2),
    }


def read_agenda(level: str, agent_id: str) -> tuple[str, list[str]]:
    """Return the authored agenda text plus why the runtime would reject it.

    The file is shown exactly as written even when invalid — an author has to be
    able to see and fix their own typo, so we never silently substitute a
    normalized document for what is actually on disk.
    """
    path = _agent_path(level, agent_id, "agenda.json")
    if not path.exists():
        return AGENDA_STARTER, []
    text = path.read_text(encoding="utf-8")
    return text, validate_agenda_text(text)[1]


def validate_agenda_text(text: str) -> tuple[dict | None, list[str]]:
    """Parse + validate agenda JSON, returning the document or its errors.

    Mirrors ``Agent.load`` so the cockpit rejects exactly what the runtime
    rejects, with the same wording.
    """
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"]
    try:
        return agenda.validate_document(raw), []
    except agenda.AgendaValidationError as exc:
        return None, list(exc.errors)


def _form_int(form: dict, key: str, default: int) -> int:
    """A blank numeric field means "use the default"; a non-number is the
    user's mistake and must be said, not silently replaced (fail loud)."""
    raw = str(form.get(key) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{key} must be a whole number, got {raw!r} — not saved")


def save_agent(level: str, agent_id: str, form: dict) -> None:
    # Validate before any directory or file is touched: a rejected create must
    # not leave an empty agent folder behind to block the retry.
    tier = _form_int(form, "tier", 2)
    tick_interval = _form_int(form, "tick_interval_seconds", 10)
    speech_cooldown = _form_int(form, "speech_cooldown_seconds", 30)

    agents_dir = _agents_dir(level)
    agents_dir.mkdir(parents=True, exist_ok=True)
    base = _contained(agents_dir, _path_id(agent_id, "agent"))
    base.mkdir(parents=True, exist_ok=True)

    # Preserve runtime fields from existing state; only overwrite config fields
    state_path = _contained(base, "state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    state.update({
        "agent_id": agent_id,
        "unreal_actor_name": form.get("unreal_actor_name") or agent_id.title(),
        "blueprint_class": form.get("blueprint_class", ""),
        "tier": tier,
        "is_active": form.get("is_active") == "on",
        "is_busy": state.get("is_busy", False),
        "current_goal": form.get("current_goal", "idle"),
        "tick_interval_seconds": tick_interval,
        "speech_cooldown_seconds": speech_cooldown,
    })
    state.setdefault("last_tick_time", None)
    state.setdefault("last_spoke_time", None)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    _contained(base, "character.md").write_text(form.get("character", ""), encoding="utf-8")
    _contained(base, "goals.md").write_text(form.get("goals", ""), encoding="utf-8")
    _contained(base, "rules.md").write_text(form.get("rules", ""), encoding="utf-8")

    actions = [a.strip() for a in (form.get("allowed_actions") or "").splitlines() if a.strip()]
    _contained(base, "tools.json").write_text(
        json.dumps({"allowed_actions": actions}, indent=2), encoding="utf-8")

    mem_path = _contained(base, "memory.json")
    if not mem_path.exists():
        mem_path.write_text(json.dumps({"agent_id": agent_id, "memories": []}, indent=2), encoding="utf-8")


def _resolve_level(level: str = None) -> str | None:
    """Pick the world to show: an explicit ?level=, else the first world dir."""
    if level:
        _world_dir(level)
        return level
    worlds = list_worlds()
    return worlds[0] if worlds else None


def _map_image_url(level: str) -> str | None:
    """URL of the real top-down world capture drawn under the grid (#6c).

    A per-level ``images/<level>.png`` wins; the shared ``world_map_view.png``
    is the fallback. The capture must frame the whole world exactly, so
    bounds→pixel is a plain linear map (the #6c calibration assumption:
    +X = east = right, +Y = south = down, row 0 = north/top).
    """
    for name in (f"{level}.png", "world_map_view.png"):
        if name != "world_map_view.png":
            _path_id(level, "world")
        path = _contained(BASE_DIR / "images", name)
        if path.exists():
            # mtime cache-buster: a re-shot capture (#18) must show up on the
            # next page load, not whenever the browser drops its cache.
            return f"/images/{name}?v={int(path.stat().st_mtime)}"
    return None


def build_map(level: str) -> dict:
    """Assemble the map view for a world from its grid file + shared PlaceDB.

    Reads ``worlds/<level>/world_grid.json`` (dims) and ``world_places.db``
    (named/swept cells). Never creates the DB — a missing DB yields an empty
    map, so a GET can't spawn a blank world. Shape::

        {level, cell_size, has_bounds, cols, rows, bounds, origin_x, origin_y,
         image_url, cells: [...], owned: [{col,row,owner,name,dx,dy,extent_cm}],
         counts: {named, surveyed, swept, mapped, stale, owned, total_cells}}

    ``bounds``/``origin_x``/``origin_y`` (world cm) + ``image_url`` let the page
    draw the grid and place cells over the real top-down capture (#6c):
    cell (c, r)'s min corner is (origin + c·cell_size) mapped linearly into the
    rectangle the image frames — ``image_bounds`` when the grid file calibrates
    one (a capture that doesn't frame ``bounds`` exactly), else ``bounds``.
    """
    grid = WorldGrid.load(_world_path(level, "world_grid.json"))
    cols = rows = None
    if grid.has_bounds:
        probe = grid.locate(grid.bounds["min_x"], grid.bounds["min_y"])
        cols, rows = probe["cols"], probe["rows"]
    origin = grid.origin()

    db_path = _world_path(level, "world_places.db")
    db = PlaceDB(db_path) if db_path.exists() else None
    cells = db.map_cells(max_age_seconds=MAP_STALE_SECONDS) if db else []
    for cell in cells:
        image_id = cell.get("place_image_id")
        cell["place_image_url"] = (
            "/api/map/place-image?" + urlencode({"level": level, "place_image_id": image_id})
            if image_id else None
        )
    owned = db.all_owned_places() if db else []
    # Ground someone ruled out, and why (#80). Refusals are cells; no-go
    # patches are sub-cell circles (#78). Shown, never editable from the map:
    # withdrawing one stays the APC's own act (allow_cell).
    refusals = db.all_refusals() if db else []
    # Every patch ever written, marked with whether it still steers a step (#91).
    # `all_patches` is the whole record and `active_patches` is the live subset,
    # so the difference IS the expired set — no second age rule to keep in sync.
    no_go = db.all_patches() if db else []
    live_ids = {p["id"] for p in db.active_patches()} if db else set()
    named = sum(1 for c in cells if c["named"])
    swept = sum(1 for c in cells if c["swept"])
    surveyed = sum(1 for c in cells if c["surveyed"])
    stale = sum(1 for c in cells if c.get("stale"))
    return {
        "level": level,
        "cell_size": grid.cell_size,
        "has_bounds": grid.has_bounds,
        "cols": cols,
        "rows": rows,
        "bounds": grid.bounds,
        "image_bounds": grid.image_bounds,
        "origin_x": origin[0] if origin else None,
        "origin_y": origin[1] if origin else None,
        "logical_origin_x": grid.origin_x,
        "logical_origin_y": grid.origin_y,
        "image_url": _map_image_url(level),
        "stale_after_hours": MAP_STALE_SECONDS // 3600,
        "cells": cells,
        "owned": [{"col": o["col"], "row": o["row"], "owner": o["owner"], "name": o["name"],
                   "dx": o["dx"], "dy": o["dy"], "extent_cm": o["extent_cm"]}
                  for o in owned],
        "refusals": [{"col": r["col"], "row": r["row"], "refused_by": r["refused_by"],
                      "reason": r["reason"], "refused_at": r["refused_at"]}
                     for r in refusals],
        "no_go": [{"x": p["x"], "y": p["y"], "radius_cm": p["radius_cm"],
                   "refused_by": p["refused_by"], "reason": p["reason"],
                   "refused_at": p["refused_at"],
                   # Who wrote it and on what evidence (#91). A judgement the
                   # APC stated and a reading its own body took are different
                   # facts, and a map that draws them the same hides the one
                   # thing worth watching: where the world walls an APC in.
                   "source": p.get("source") or "stated",
                   "proofs": p.get("proofs") or 0,
                   "expired": p["id"] not in live_ids}
                  for p in no_go],
        "counts": {"named": named, "surveyed": surveyed, "swept": swept,
                   "mapped": len(cells), "stale": stale, "owned": len(owned),
                   "refused": len({(r["col"], r["row"]) for r in refusals}),
                   "no_go": len(no_go),
                   "no_go_measured": sum(1 for p in no_go
                                         if (p.get("source") or "stated") == "measured"),
                   "no_go_expired": sum(1 for p in no_go if p["id"] not in live_ids),
                   "total_cells": (cols or 0) * (rows or 0)},
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    worlds = list_worlds()
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "worlds": worlds,
        "world_agents": {w: list_agents(w) for w in worlds},
        "current_level": unreal_client.get_current_level(),
        "setup": setup_status(ENV_PATH),
    })



@app.get("/map", response_class=HTMLResponse)
async def map_page(request: Request, level: str = None):
    """Live map view — watch the grid + place cells get built out."""
    worlds = list_worlds()
    level = _resolve_level(level)
    data = build_map(level) if level else None
    return templates.TemplateResponse(request, "map.html", {
        "request": request,
        "worlds": worlds,
        "level": level,
        "map": data,
        "agents": list_agents(level) if level else [],   # author-mode owner dropdown (#16)
    })


@app.get("/api/map")
async def api_map(level: str = None):
    """JSON grid state for the map view; polled by the page to animate build-out."""
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"level": None, "cols": None, "rows": None,
                             "cells": [], "counts": {"named": 0, "swept": 0, "total_cells": 0}})
    return JSONResponse(build_map(level))


@app.get("/api/map/place-image")
async def api_map_place_image(place_image_id: str, level: str = None):
    """Serve one durable community/owned place composite referenced by PlaceDB."""
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"error": "not found"}, status_code=404)
    world_dir = _world_dir(level)
    db_path = _world_path(level, "world_places.db")
    if not db_path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    db = PlaceDB(db_path)
    image = db.place_image(place_image_id)
    if not image:
        return JSONResponse({"error": "not found"}, status_code=404)
    path = db.absolute_image_path(image).resolve()
    if world_dir not in path.parents or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(str(path), media_type="image/png")


@app.post("/api/world/sync")
async def api_world_sync(level: str = None):
    """"I moved things — sync the world" (#21 v1, upgraded by #23): purge
    wake-seeded places, then rescan Landmark_* actors in the level and
    re-apply the manifest (landmarks + places.json, landmark wins on
    collision) so a moved/renamed landmark converges immediately — this *is*
    the #21 v2 re-anchor.

    Editor moves make wake seeds stale (agents hunt the old spots); deleting
    them is self-healing — the next run re-seeds at the new day-start
    positions. Authored (landmark/places.json) and runtime (agent-discovered)
    rows are never touched by the purge. The purge itself never creates the
    DB (count 0 is an honest "nothing to sync"); the landmark rescan does
    open/create the world's PlaceDB, since it may be this world's first sync.
    """
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"level": None, "deleted": [], "count": 0,
                             "landmarks": 0, "applied": {"applied": 0, "owned": 0,
                                                          "community": 0, "skipped": 0},
                             "landmark_places": [], "suspects": []})
    db_path = _world_path(level, "world_places.db")
    deleted = []
    if db_path.exists():
        deleted = [{"owner": r["owner"], "name": r["name"], "col": r["col"], "row": r["row"]}
                   for r in PlaceDB(db_path).purge_wake_seeds()]

    scanned = scan_landmarks(unreal_client.get_actors())
    landmarks = scanned["entries"]
    suspects = scanned["suspects"]
    merged = merge_entries(landmarks, places_manifest.load_manifest(_places_path(level)))
    grid = WorldGrid.load(_world_path(level, "world_grid.json"))
    applied = places_manifest.apply_manifest(PlaceDB(db_path), grid, merged)
    landmark_places = [f"{e['owner'] or 'community'}/{e['name']}" for e in landmarks]

    return JSONResponse({"level": level, "deleted": deleted, "count": len(deleted),
                         "landmarks": len(landmarks), "applied": applied,
                         "landmark_places": landmark_places, "suspects": suspects})


# ── Map capture (#18): shoot the world map from the MAP_Camera pawn ───────────
# The pose math + engine-capture constants live in agent_runtime.map_capture
# (shared with AgentManager.generate_world_grid's registration shot); this
# route is the on-demand "Re-shoot map" path over the web UI's direct socket.


@app.post("/api/map/capture")
async def api_map_capture(level: str = None, actor: str = None):
    """Re-shoot the world map (#18): aim MAP_Camera top-down over the world
    bounds, capture to ``images/<level>.png``, and write the frame's
    ``image_bounds`` into ``world_grid.json`` — the /map overlay is then
    registered by construction. Fails loud at every step; never guesses.
    """
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"ok": False, "error": "no world selected"}, status_code=400)
    grid_path = _world_path(level, "world_grid.json")
    grid = WorldGrid.load(grid_path)
    if not grid.has_bounds:
        return JSONResponse(
            {"ok": False, "error": f"{level} has no world_grid.json bounds — "
             "generate the grid first"}, status_code=400)

    pose = camera_pose_for_bounds(grid.bounds)
    actor = actor or MAP_CAMERA_ACTOR
    moved = unreal_client.set_actor_transform(actor, pose["location"], pose["rotation"])
    if not moved or moved.get("status") == "error":
        return JSONResponse(
            {"ok": False, "error": f"could not position '{actor}': "
             f"{(moved or {}).get('error', 'Unreal not reachable')}"}, status_code=502)

    image_file = _contained(BASE_DIR / "images", f"{_path_id(level, 'world')}.png")
    shot = unreal_client.capture_camera_image(actor, str(image_file))
    inner = (shot or {}).get("result") if isinstance((shot or {}).get("result"), dict) else (shot or {})
    if not shot or shot.get("status") == "error" or not inner.get("success"):
        return JSONResponse(
            {"ok": False, "error": f"capture failed on '{actor}': "
             f"{(shot or {}).get('error', 'Unreal not reachable')}"}, status_code=502)

    # The capture frames exactly pose["image_bounds"] — persist the calibration.
    raw = json.loads(grid_path.read_text(encoding="utf-8"))
    raw["image_bounds"] = pose["image_bounds"]
    grid_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    return JSONResponse({
        "ok": True,
        "level": level,
        "actor": inner.get("actor_name", actor),
        "image_url": f"/images/{level}.png",
        "camera": {"location": pose["location"], "rotation": pose["rotation"]},
        "image_bounds": pose["image_bounds"],
    })


@app.get("/replay", response_class=HTMLResponse)
async def replay_page(request: Request, level: str = None):
    """Run replay — single-step a sim run's observation frames next to decisions (#14)."""
    worlds = list_worlds()
    level = _resolve_level(level)
    return templates.TemplateResponse(request, "replay.html", {
        "request": request,
        "worlds": worlds,
        "level": level,
    })


# ── Authored places editor (#16): click-to-author on the registered map ───────
# The manifest (places.json, WP6) is the user's ground truth; this is the
# no-Unreal way to write it — click a spot on the registered map, name it,
# done. Every edit re-applies the whole manifest (declarative converge), so
# moves and deletes take effect in PlaceDB immediately.

def _norm_place_name(name) -> str:
    return " ".join(str(name or "").split()).lower()


def _places_path(level: str) -> Path:
    return _world_path(level, "places.json")


def _read_places_raw(level: str) -> dict | None:
    """The raw manifest dict, ``{"places": []}`` when absent, None when corrupt.

    Corrupt is surfaced, never healed silently — rewriting a file we could
    not parse would destroy whatever the user meant it to say.
    """
    path = _places_path(level)
    if not path.exists():
        return {"places": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data.get("places"), list):
            return None
        return data
    except Exception:
        return None


def _apply_places(level: str) -> dict:
    """Re-apply the manifest to the world's PlaceDB (authored rows converge)."""
    grid = WorldGrid.load(_world_path(level, "world_grid.json"))
    entries = places_manifest.load_manifest(_places_path(level))
    db = PlaceDB(_world_path(level, "world_places.db"))
    return places_manifest.apply_manifest(db, grid, entries)


@app.get("/api/places")
async def api_places_list(level: str = None):
    """The raw authored manifest — what the author panel lists and edits."""
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"level": None, "places": []})
    raw = _read_places_raw(level)
    if raw is None:
        return JSONResponse({"ok": False, "error": "places.json is unparseable — "
                             "fix it by hand before authoring here"}, status_code=500)
    return JSONResponse({"level": level, "places": raw["places"]})


@app.post("/api/places")
async def api_places_upsert(request: Request):
    """Create or move/edit one authored place (same name = same place).

    Body: ``{level, name, x, y, owner?, community?, extent_cm?}`` — x/y in
    world cm (the map click). Validates like the manifest loader (fail loud),
    writes places.json, and re-applies it to PlaceDB immediately.
    """
    body = await _maybe_json(request)
    level = _resolve_level(body.get("level"))
    if not level:
        return JSONResponse({"ok": False, "error": "no world selected"}, status_code=400)

    name = str(body.get("name") or "").strip()
    if not name or name.lower() in ("null", "none", "unknown"):
        return JSONResponse({"ok": False, "error": "a place needs a usable name"},
                            status_code=400)
    try:
        x, y = float(body["x"]), float(body["y"])
    except (KeyError, TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "numeric x and y are required"},
                            status_code=400)
    grid = WorldGrid.load(_world_path(level, "world_grid.json"))
    if not grid.has_bounds:
        return JSONResponse({"ok": False, "error": f"{level} has no world_grid.json "
                             "bounds — generate the grid first"}, status_code=400)
    if not grid.locate(x, y).get("in_bounds"):
        return JSONResponse({"ok": False, "error": f"({x:.0f}, {y:.0f}) is outside "
                             "the world bounds"}, status_code=400)
    try:
        extent = float(body.get("extent_cm") or PLACE_EXTENT_CM)
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "extent_cm must be numeric"},
                            status_code=400)

    entry: dict = {"name": name, "x": x, "y": y}
    owner = str(body["owner"]).strip() if body.get("owner") else None
    if owner:
        entry["owner"] = owner
    if body.get("community") is not None:
        entry["community"] = bool(body["community"])
    if extent != PLACE_EXTENT_CM:
        entry["extent_cm"] = extent

    raw = _read_places_raw(level)
    if raw is None:
        return JSONResponse({"ok": False, "error": "places.json is unparseable — "
                             "fix it by hand before authoring here"}, status_code=500)
    needle = _norm_place_name(name)
    places = raw["places"]
    replaced = False
    for i, p in enumerate(places):
        if isinstance(p, dict) and _norm_place_name(p.get("name")) == needle:
            places[i] = entry
            replaced = True
            break
    if not replaced:
        places.append(entry)
    _places_path(level).write_text(json.dumps(raw, indent=2), encoding="utf-8")

    return JSONResponse({"ok": True, "level": level, "entry": entry,
                         "replaced": replaced, "applied": _apply_places(level)})


@app.delete("/api/places")
async def api_places_delete(level: str = None, name: str = ""):
    """Remove one authored place by name; the re-apply drops its PlaceDB rows."""
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"ok": False, "error": "no world selected"}, status_code=400)
    raw = _read_places_raw(level)
    if raw is None:
        return JSONResponse({"ok": False, "error": "places.json is unparseable — "
                             "fix it by hand before authoring here"}, status_code=500)
    needle = _norm_place_name(name)
    keep = [p for p in raw["places"]
            if not (isinstance(p, dict) and _norm_place_name(p.get("name")) == needle)]
    if len(keep) == len(raw["places"]):
        return JSONResponse({"ok": False, "error": f"no authored place named '{name}'"},
                            status_code=404)
    removed = len(raw["places"]) - len(keep)
    raw["places"] = keep
    _places_path(level).write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return JSONResponse({"ok": True, "level": level, "removed": removed,
                         "applied": _apply_places(level)})


@app.get("/api/map/agents")
async def api_map_agents():
    """Live agent positions for the map overlay (#18), proxied from the runner.

    ``{"online": false, "agents": []}`` when no runner is reachable — the map
    then simply shows no dots (never stale ones).
    """
    try:
        return JSONResponse({"online": True, "agents": get_runner().positions()})
    except Exception:
        return JSONResponse({"online": False, "agents": []})


@app.get("/api/replay/runs")
async def api_replay_runs(level: str = None):
    """Run tags + agents available to replay for a world."""
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"level": None, "runs": [], "agents": []})
    return JSONResponse({
        "level": level,
        "runs": _replay_runs(level),
        "agents": list_agents(level),
    })


@app.get("/api/replay/frames")
async def api_replay_frames(run: str, agent: str, level: str = None):
    """Ordered frames for one run+agent, each with its joined decision + image URL."""
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"frames": []})
    world_dir = _world_dir(level)
    _replay_observations(level, agent)
    _world_path(level, "logs", "agent_decisions.log")
    frames = run_replay.list_frames(world_dir, run, _path_id(agent, "agent"))
    for fr in frames:
        fr["image_url"] = (f"/api/replay/image?level={level}"
                           f"&agent={agent}&file={fr['filename']}")
    return JSONResponse({"level": level, "run": run, "agent": agent, "frames": frames})


@app.get("/api/replay/image")
async def api_replay_image(agent: str, file: str, level: str = None):
    """Serve one observation PNG. Guards against path traversal: the name must be
    a well-formed SR frame and resolve inside that agent's observations dir."""
    level = _resolve_level(level)
    if not level or not run_replay.is_frame_name(file):
        return JSONResponse({"error": "not found"}, status_code=404)
    obs_dir = _agent_path(level, agent, "observations", must_exist=True)
    path = _contained(obs_dir, file)
    if not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(str(path), media_type="image/png")


@app.get("/worlds/{level}/agents/new", response_class=HTMLResponse)
async def new_agent_form(request: Request, level: str):
    _world_dir(level)
    return templates.TemplateResponse(request, "agent.html", {
        "request": request,
        "level": level,
        "agent_id": "",
        "is_new": True,
        "saved": False,
        "error": None,
        "state": {"tier": 2, "is_active": True, "tick_interval_seconds": 10, "speech_cooldown_seconds": 30},
        "character": "",
        "goals": "",
        "rules": "# Rules\n\n- Do not invent tools or actions.\n- Return structured JSON decisions only.",
        "allowed_actions": "\n".join(DEFAULT_ACTIONS),
        "agenda_text": AGENDA_STARTER,
        "agenda_errors": [],
        "raw_state": None,
        "raw_tools": None,
        "raw_memory": None,
    })


@app.post("/worlds/{level}/agents/new")
async def create_agent(request: Request, level: str):
    _world_dir(level)
    form = dict(await request.form())
    agent_id = (form.get("agent_id") or "").strip().lower()

    error = None
    if not agent_id:
        error = "agent_id is required"
    elif not re.match(r'^[a-z0-9_]+$', agent_id):
        error = "agent_id must be lowercase letters, numbers, and underscores only"
    elif _contained(_agents_dir(level), agent_id).exists():
        error = f"Agent '{agent_id}' already exists in {level}"

    if not error:
        try:
            save_agent(level, agent_id, form)
        except ValueError as exc:
            error = str(exc)

    if error:
        return templates.TemplateResponse(request, "agent.html", {
            "request": request,
            "level": level,
            "agent_id": agent_id,
            "is_new": True,
            "saved": False,
            "error": error,
            "state": form,
            "character": form.get("character", ""),
            "goals": form.get("goals", ""),
            "rules": form.get("rules", ""),
            "allowed_actions": form.get("allowed_actions", ""),
            "agenda_text": AGENDA_STARTER,
            "agenda_errors": [],
        })

    return RedirectResponse(f"/worlds/{level}/agents/{agent_id}?saved=1", status_code=303)


@app.get("/worlds/{level}/agents/{agent_id}", response_class=HTMLResponse)
async def edit_agent_form(request: Request, level: str, agent_id: str, saved: bool = False):
    try:
        data = load_agent(level, agent_id)
    except FileNotFoundError:
        return HTMLResponse("Agent not found", status_code=404)
    return templates.TemplateResponse(request, "agent.html", {
        "request": request,
        "level": level,
        "agent_id": agent_id,
        "is_new": False,
        "saved": saved,
        "error": None,
        **data,
    })


@app.post("/worlds/{level}/agents/{agent_id}")
async def update_agent(request: Request, level: str, agent_id: str):
    _agent_dir(level, agent_id, must_exist=True)
    form = dict(await request.form())
    try:
        save_agent(level, agent_id, form)
    except ValueError as exc:
        # Nothing was written — re-render with the rejection and the user's
        # text kept on screen, same contract as the agenda editor (fail loud).
        data = load_agent(level, agent_id)
        data.update({
            "state": form,
            "character": form.get("character", ""),
            "goals": form.get("goals", ""),
            "rules": form.get("rules", ""),
            "allowed_actions": form.get("allowed_actions", ""),
        })
        return templates.TemplateResponse(request, "agent.html", {
            "request": request,
            "level": level,
            "agent_id": agent_id,
            "is_new": False,
            "saved": False,
            "error": str(exc),
            **data,
        })
    return RedirectResponse(f"/worlds/{level}/agents/{agent_id}?saved=1", status_code=303)


@app.post("/worlds/{level}/agents/{agent_id}/agenda")
async def update_agent_agenda(request: Request, level: str, agent_id: str):
    """Validate and atomically replace one APC's authored agenda (#43).

    Deliberately separate from ``update_agent``: this route touches only
    ``agenda.json``, so saving an agenda can never overwrite character/goals/
    rules, and a rejected document leaves the previous agenda running rather
    than half-writing one the runtime would then execute.
    """
    _agent_dir(level, agent_id, must_exist=True)
    form = dict(await request.form())
    text = form.get("agenda_text", "")

    document, errors = validate_agenda_text(text)
    if document is not None:
        try:
            agenda.write_document(_agent_path(level, agent_id, "agenda.json"), document)
        except OSError as exc:
            errors = [f"could not write agenda.json: {exc.strerror or exc}"]

    if errors:
        data = load_agent(level, agent_id)
        # Keep the rejected text on screen; the file on disk is unchanged.
        data["agenda_text"] = text
        data["agenda_errors"] = errors
        return templates.TemplateResponse(request, "agent.html", {
            "request": request,
            "level": level,
            "agent_id": agent_id,
            "is_new": False,
            "saved": False,
            "error": None,
            **data,
        })
    return RedirectResponse(f"/worlds/{level}/agents/{agent_id}?saved=1#agenda",
                            status_code=303)


@app.post("/worlds/{level}/agents/{agent_id}/delete")
async def delete_agent(level: str, agent_id: str):
    import shutil
    path = _agent_dir(level, agent_id, must_exist=True)
    shutil.rmtree(path)
    return RedirectResponse("/", status_code=303)


@app.get("/api/unreal/actors")
async def api_actors():
    actors = unreal_client.get_actors()
    labels = sorted({a.get("label") or a.get("name", "") for a in actors if a.get("label") or a.get("name")})
    return JSONResponse({"online": bool(actors), "actors": labels})


# ── Sim controller (cockpit over the standalone sim_runner) ───────────────────

RUNNER_URL = DEFAULT_BASE_URL   # where sim_runner.py serves its control API


def get_runner() -> RunnerClient:
    """The control client for the standalone sim runner (overridable in tests)."""
    return RunnerClient(base_url=RUNNER_URL)


@app.get("/sim", response_class=HTMLResponse)
async def sim_page(request: Request):
    return templates.TemplateResponse(request, "sim.html", {
        "request": request,
        "runner_url": RUNNER_URL,
        "setup": setup_status(ENV_PATH),
    })


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html", {
        "request": request,
        "runner_url": RUNNER_URL,
    })


@app.get("/api/sim/status")
def api_sim_status():
    """Runner status, or ``{"online": false}`` when no runner is reachable."""
    try:
        return JSONResponse({"online": True, **get_runner().status()})
    except Exception:
        return JSONResponse({"online": False})


@app.get("/api/sim/events")
def api_sim_events(limit: int = 30):
    try:
        return JSONResponse({"events": get_runner().events(limit)})
    except Exception:
        return JSONResponse({"events": []})


@app.post("/api/sim/events/clear")
def api_sim_events_clear():
    """Empty the decision feed (clears agent_decisions.log; memories untouched)."""
    try:
        return JSONResponse(get_runner().clear_events())
    except Exception:
        return JSONResponse({"cleared": 0})


@app.post("/api/sim/start")
async def api_sim_start(request: Request):
    body = await _maybe_json(request)
    return JSONResponse(get_runner().start(
        tick_seconds=int(body.get("tick_seconds", 1)),
        active_agents=body.get("active_agents"),
        mode=body.get("mode", "play"),
    ))


@app.post("/api/sim/stop")
def api_sim_stop():
    return JSONResponse(get_runner().stop())


@app.post("/api/sim/tick")
def api_sim_tick():
    """Advance exactly one tick — the single-step debugging control."""
    return JSONResponse(get_runner().tick())


@app.post("/api/sim/reset_day")
def api_sim_reset_day():
    """Restart the sim from morning — fresh day, memories + place cells preserved."""
    return JSONResponse(get_runner().reset_day())


@app.post("/api/sim/reset_agents")
def api_sim_reset_agents():
    """Teleport agents to their start spots and wipe learned memories (restores
    memory.seed.json if present)."""
    return JSONResponse(get_runner().reset_agents())


@app.post("/api/sim/reset_places")
def api_sim_reset_places():
    """Wipe the shared world map DB — landmarks re-apply on next sim start."""
    return JSONResponse(get_runner().reset_places())


@app.post("/api/sim/capture_starts")
def api_sim_capture_starts():
    """Adopt current placed APC transforms as future reset/start positions."""
    return JSONResponse(get_runner().capture_starts())


@app.get("/api/sim/agents/{agent_id}")
def api_sim_agent(agent_id: str):
    """Inspect one loaded APC, including durable chat/interruption state."""
    try:
        return JSONResponse(get_runner().inspect_agent(agent_id))
    except Exception:
        return JSONResponse({"status": "error", "error": "no sim runner running"},
                            status_code=503)


@app.post("/api/sim/agents/{agent_id}/chat/start")
async def api_sim_chat_start(agent_id: str, request: Request):
    body = await _maybe_json(request)
    try:
        return JSONResponse(get_runner().start_chat(agent_id, str(body.get("source", ""))))
    except Exception:
        return JSONResponse({"status": "error", "error": "no sim runner running"},
                            status_code=503)


@app.post("/api/sim/agents/{agent_id}/chat/message")
async def api_sim_chat_message(agent_id: str, request: Request):
    body = await _maybe_json(request)
    try:
        return JSONResponse(get_runner().send_chat_message(
            agent_id, str(body.get("message", ""))))
    except Exception:
        return JSONResponse({"status": "error", "error": "chat message failed"},
                            status_code=503)


@app.post("/api/sim/agents/{agent_id}/chat/guide")
async def api_sim_chat_guide(agent_id: str, request: Request):
    body = await _maybe_json(request)
    try:
        return JSONResponse(get_runner().guide_from_chat(
            agent_id, str(body.get("direction", ""))))
    except Exception:
        return JSONResponse({"status": "error", "error": "guidance failed"},
                            status_code=503)


@app.post("/api/sim/agents/{agent_id}/chat/end")
def api_sim_chat_end(agent_id: str):
    try:
        return JSONResponse(get_runner().end_chat(agent_id))
    except Exception:
        return JSONResponse({"status": "error", "error": "chat release failed"},
                            status_code=503)


async def _maybe_json(request: Request) -> dict:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@app.post("/api/world/grid")
async def api_world_grid(request: Request):
    """Generate the world grid from the cockpit (#13.2) — proxy to the standalone
    runner's ``generate_world_grid`` (needs the editor open with PIE stopped; the
    runner is the bridge's sole owner). No runner reachable -> the same
    "no sim runner running" envelope the other ``/api/sim/*`` proxies use, just
    with ``ok``/``error`` fields so the /map callout can surface the failure.
    """
    body = await _maybe_json(request)
    try:
        cell_size = float(body.get("cell_size", 3000))
        padding = float(body.get("padding", 800))
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "cell_size/padding must be numbers"},
                            status_code=400)
    try:
        result = get_runner().generate_world_grid(cell_size=cell_size, padding=padding)
    except Exception:
        return JSONResponse({"ok": False, "error": "no sim runner running"}, status_code=503)
    if result.get("status") == "error":
        return JSONResponse({"ok": False, "error": result.get("error", "grid generation failed")},
                            status_code=400)
    return JSONResponse({"ok": True, **result})


@app.post("/api/world/regrid")
async def api_world_regrid(request: Request):
    """Commit a previewed logical origin through the runner's reset transaction."""
    body = await _maybe_json(request)
    if body.get("confirm") is not True:
        return JSONResponse({"ok": False, "error": "explicit confirmation required"},
                            status_code=400)
    try:
        level = str(body.get("level", ""))
        origin_x = float(body.get("origin_x"))
        origin_y = float(body.get("origin_y"))
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "origin_x/origin_y must be numbers"},
                            status_code=400)
    _world_dir(level, must_exist=False)
    try:
        result = get_runner().regrid(level, origin_x, origin_y)
    except Exception:
        return JSONResponse({"ok": False, "error": "no sim runner running"}, status_code=503)
    if result.get("status") == "error":
        return JSONResponse({"ok": False, "error": result.get("error", "regrid failed")},
                            status_code=400)
    return JSONResponse({"ok": True, **result})


# ── Settings ──────────────────────────────────────────────────────────────────

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", {
        "request": request,
        "config": read_config(ENV_PATH),
    })


@app.get("/api/settings")
async def api_settings():
    """Current config; secret values are masked (set/unset only)."""
    return JSONResponse(read_config(ENV_PATH))


@app.get("/api/setup")
async def api_setup():
    """First-run readiness — drives the setup banner (backlog #13.1)."""
    return JSONResponse(setup_status(ENV_PATH))


@app.post("/settings")
async def settings_save(request: Request):
    """Persist edited config to .env. A blank secret field means "leave as-is" —
    so the form (which never receives secret values) can't wipe a key."""
    form = await request.form()
    updates = {
        key: value for key, value in form.items()
        if not (is_secret(key) and value == "")
    }
    write_config(ENV_PATH, updates)
    # The sim process reloads .env before each LLM decision, so writing is enough.
    return RedirectResponse("/settings", status_code=303)


# ── Provider profiles (CRUD) ────────────────────────────────────────────────────
# Named {provider, model} profiles assigned to the decision/vision roles. Any
# mutation re-compiles the active roles into .env (apply_to_env), so the running
# sim — which reloads .env each tick — picks up the change with no restart.

@app.get("/providers", response_class=HTMLResponse)
async def providers_page(request: Request):
    return templates.TemplateResponse(request, "providers.html", {
        "request": request,
        "data": provider_profiles.read_profiles(CONFIG_PATH),
        "roles": provider_profiles.ROLES,
    })


@app.get("/api/providers")
async def api_providers():
    """Current profiles + role assignments. Holds no secrets (keys live in .env)."""
    return JSONResponse(provider_profiles.read_profiles(CONFIG_PATH))


@app.post("/providers/save")
async def providers_save(request: Request):
    """Create or update a profile (form: name, provider, model)."""
    form = await request.form()
    data = provider_profiles.read_profiles(CONFIG_PATH)
    try:
        provider_profiles.upsert_profile(
            data, str(form.get("name", "")),
            str(form.get("provider", "")), str(form.get("model", "")),
        )
    except ValueError:
        return RedirectResponse("/providers", status_code=303)
    provider_profiles.write_profiles(CONFIG_PATH, data)
    provider_profiles.apply_to_env(data, ENV_PATH)
    return RedirectResponse("/providers", status_code=303)


@app.post("/providers/delete")
async def providers_delete(request: Request):
    """Delete a profile (form: name) and unassign any role using it."""
    form = await request.form()
    data = provider_profiles.read_profiles(CONFIG_PATH)
    provider_profiles.delete_profile(data, str(form.get("name", "")))
    provider_profiles.write_profiles(CONFIG_PATH, data)
    provider_profiles.apply_to_env(data, ENV_PATH)
    return RedirectResponse("/providers", status_code=303)


@app.post("/providers/assign")
async def providers_assign(request: Request):
    """Point a role at a profile (form: role, profile) and apply it to .env."""
    form = await request.form()
    data = provider_profiles.read_profiles(CONFIG_PATH)
    try:
        provider_profiles.assign_role(data, str(form.get("role", "")), str(form.get("profile", "")))
    except ValueError:
        return RedirectResponse("/providers", status_code=303)
    provider_profiles.write_profiles(CONFIG_PATH, data)
    provider_profiles.apply_to_env(data, ENV_PATH)
    return RedirectResponse("/providers", status_code=303)


LOG_PATH = BASE_DIR.parent / "unreal_mcp.log"


@app.get("/api/log/dates")
async def api_log_dates():
    if not LOG_PATH.exists():
        return JSONResponse({"dates": []})
    seen: list[str] = []
    seen_set: set[str] = set()
    with LOG_PATH.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(line) >= 10 and line[4] == "-" and line[7] == "-":
                d = line[:10]
                if d not in seen_set:
                    seen_set.add(d)
                    seen.append(d)
    return JSONResponse({"dates": seen})


@app.get("/api/log")
async def api_log(date: str = ""):
    if not LOG_PATH.exists():
        return JSONResponse({"content": ""})
    if not date:
        return JSONResponse({"content": LOG_PATH.read_text(encoding="utf-8", errors="replace")})
    lines: list[str] = []
    with LOG_PATH.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith(date):
                lines.append(line)
    return JSONResponse({"content": "".join(lines)})


@app.post("/api/log/delete")
async def api_log_delete():
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    return JSONResponse({"status": "deleted"})


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
