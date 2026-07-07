"""Unreal World Sim — local web UI for managing agents under Python/worlds/."""

import json
import re
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agent_runtime.config_store import read_config, write_config, is_secret
from agent_runtime import provider_profiles
from agent_runtime import run_replay
from agent_runtime.runner_client import RunnerClient, DEFAULT_BASE_URL
from agent_runtime.place_db import PlaceDB
from agent_runtime.world_grid import WorldGrid
from web_ui import unreal_client

BASE_DIR = Path(__file__).parent
WORLDS_DIR = BASE_DIR.parent / "worlds"
ENV_PATH = BASE_DIR.parent / ".env"   # provider/model config the settings page manages
CONFIG_PATH = BASE_DIR.parent / "config.json"   # named provider profiles + role assignments
MAP_STALE_SECONDS = 24 * 3600   # a place cell older than this is flagged for re-observation

app = FastAPI(title="Unreal World Sim")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/images", StaticFiles(directory=str(BASE_DIR / "images")), name="images")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

DEFAULT_ACTIONS = [
    "idle", "walk_to", "speak_to", "inspect_object",
    "follow_character", "attack", "flee", "observe", "remember",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def list_worlds() -> list[str]:
    if not WORLDS_DIR.exists():
        return []
    return sorted(p.name for p in WORLDS_DIR.iterdir() if p.is_dir())


def list_agents(level: str) -> list[str]:
    agents_dir = WORLDS_DIR / level / "agents"
    if not agents_dir.exists():
        return []
    return sorted(p.name for p in agents_dir.iterdir() if p.is_dir())


def load_agent(level: str, agent_id: str) -> dict:
    base = WORLDS_DIR / level / "agents" / agent_id
    state = json.loads((base / "state.json").read_text(encoding="utf-8"))
    character = (base / "character.md").read_text(encoding="utf-8")
    goals = (base / "goals.md").read_text(encoding="utf-8")
    rules = (base / "rules.md").read_text(encoding="utf-8")
    tools = json.loads((base / "tools.json").read_text(encoding="utf-8"))
    memory_path = base / "memory.json"
    memory_raw = memory_path.read_text(encoding="utf-8") if memory_path.exists() else "{}"
    return {
        "state": state,
        "character": character,
        "goals": goals,
        "rules": rules,
        "allowed_actions": "\n".join(tools.get("allowed_actions", DEFAULT_ACTIONS)),
        # raw JSON for the viewer panel
        "raw_state": json.dumps(state, indent=2),
        "raw_tools": json.dumps(tools, indent=2),
        "raw_memory": json.dumps(json.loads(memory_raw), indent=2),
    }


def save_agent(level: str, agent_id: str, form: dict) -> None:
    base = WORLDS_DIR / level / "agents" / agent_id
    base.mkdir(parents=True, exist_ok=True)

    # Preserve runtime fields from existing state; only overwrite config fields
    state_path = base / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    state.update({
        "agent_id": agent_id,
        "unreal_actor_name": form.get("unreal_actor_name") or agent_id.title(),
        "blueprint_class": form.get("blueprint_class", ""),
        "tier": int(form.get("tier") or 2),
        "is_active": form.get("is_active") == "on",
        "is_busy": state.get("is_busy", False),
        "current_goal": form.get("current_goal", "idle"),
        "tick_interval_seconds": int(form.get("tick_interval_seconds") or 10),
        "speech_cooldown_seconds": int(form.get("speech_cooldown_seconds") or 30),
    })
    state.setdefault("last_tick_time", None)
    state.setdefault("last_spoke_time", None)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    (base / "character.md").write_text(form.get("character", ""), encoding="utf-8")
    (base / "goals.md").write_text(form.get("goals", ""), encoding="utf-8")
    (base / "rules.md").write_text(form.get("rules", ""), encoding="utf-8")

    actions = [a.strip() for a in (form.get("allowed_actions") or "").splitlines() if a.strip()]
    (base / "tools.json").write_text(json.dumps({"allowed_actions": actions}, indent=2), encoding="utf-8")

    mem_path = base / "memory.json"
    if not mem_path.exists():
        mem_path.write_text(json.dumps({"agent_id": agent_id, "memories": []}, indent=2), encoding="utf-8")


def _resolve_level(level: str = None) -> str | None:
    """Pick the world to show: an explicit ?level=, else the first world dir."""
    if level:
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
        if (BASE_DIR / "images" / name).exists():
            return f"/images/{name}"
    return None


def build_map(level: str) -> dict:
    """Assemble the map view for a world from its grid file + shared PlaceDB.

    Reads ``worlds/<level>/world_grid.json`` (dims) and ``world_places.db``
    (named/swept cells). Never creates the DB — a missing DB yields an empty
    map, so a GET can't spawn a blank world. Shape::

        {level, cell_size, has_bounds, cols, rows, bounds, origin_x, origin_y,
         image_url, cells: [...], owned: [{col,row,owner,name,dx,dy,extent_cm}],
         counts: {named, swept, stale, owned, total_cells}}

    ``bounds``/``origin_x``/``origin_y`` (world cm) + ``image_url`` let the page
    draw the grid and place cells over the real top-down capture (#6c):
    cell (c, r)'s min corner is (origin + c·cell_size) mapped linearly into the
    rectangle the image frames — ``image_bounds`` when the grid file calibrates
    one (a capture that doesn't frame ``bounds`` exactly), else ``bounds``.
    """
    grid = WorldGrid.load(WORLDS_DIR / level / "world_grid.json")
    cols = rows = None
    if grid.has_bounds:
        probe = grid.locate(grid.bounds["min_x"], grid.bounds["min_y"])
        cols, rows = probe["cols"], probe["rows"]
    origin = grid.origin()

    db_path = WORLDS_DIR / level / "world_places.db"
    db = PlaceDB(db_path) if db_path.exists() else None
    cells = db.map_cells(max_age_seconds=MAP_STALE_SECONDS) if db else []
    owned = db.all_owned_places() if db else []
    named = sum(1 for c in cells if c["state"] == "named")
    swept = sum(1 for c in cells if c["state"] == "swept")
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
        "image_url": _map_image_url(level),
        "stale_after_hours": MAP_STALE_SECONDS // 3600,
        "cells": cells,
        "owned": [{"col": o["col"], "row": o["row"], "owner": o["owner"], "name": o["name"],
                   "dx": o["dx"], "dy": o["dy"], "extent_cm": o["extent_cm"]}
                  for o in owned],
        "counts": {"named": named, "swept": swept, "stale": stale, "owned": len(owned),
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
    })


@app.get("/api/map")
async def api_map(level: str = None):
    """JSON grid state for the map view; polled by the page to animate build-out."""
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"level": None, "cols": None, "rows": None,
                             "cells": [], "counts": {"named": 0, "swept": 0, "total_cells": 0}})
    return JSONResponse(build_map(level))


@app.post("/api/world/sync")
async def api_world_sync(level: str = None):
    """"I moved things — sync the world" (#21 v1): purge wake-seeded places.

    Editor moves make wake seeds stale (agents hunt the old spots); deleting
    them is self-healing — the next run re-seeds at the new day-start
    positions. Authored (places.json) and runtime (agent-discovered) rows are
    never touched. Never creates the DB; reports exactly what was deleted —
    count 0 is an honest "nothing to sync".
    """
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"level": None, "deleted": [], "count": 0})
    db_path = WORLDS_DIR / level / "world_places.db"
    if not db_path.exists():
        return JSONResponse({"level": level, "deleted": [], "count": 0})
    deleted = [{"owner": r["owner"], "name": r["name"], "col": r["col"], "row": r["row"]}
               for r in PlaceDB(db_path).purge_wake_seeds()]
    return JSONResponse({"level": level, "deleted": deleted, "count": len(deleted)})


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


@app.get("/api/replay/runs")
async def api_replay_runs(level: str = None):
    """Run tags + agents available to replay for a world."""
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"level": None, "runs": [], "agents": []})
    world_dir = WORLDS_DIR / level
    return JSONResponse({
        "level": level,
        "runs": run_replay.list_runs(world_dir),
        "agents": run_replay.list_agents(world_dir),
    })


@app.get("/api/replay/frames")
async def api_replay_frames(run: str, agent: str, level: str = None):
    """Ordered frames for one run+agent, each with its joined decision + image URL."""
    level = _resolve_level(level)
    if not level:
        return JSONResponse({"frames": []})
    frames = run_replay.list_frames(WORLDS_DIR / level, run, agent)
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
    obs_dir = (WORLDS_DIR / level / "agents" / agent / "observations").resolve()
    path = (obs_dir / file).resolve()
    if obs_dir not in path.parents or not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(str(path), media_type="image/png")


@app.get("/worlds/{level}/agents/new", response_class=HTMLResponse)
async def new_agent_form(request: Request, level: str):
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
        "raw_state": None,
        "raw_tools": None,
        "raw_memory": None,
    })


@app.post("/worlds/{level}/agents/new")
async def create_agent(request: Request, level: str):
    form = dict(await request.form())
    agent_id = (form.get("agent_id") or "").strip().lower()

    error = None
    if not agent_id:
        error = "agent_id is required"
    elif not re.match(r'^[a-z0-9_]+$', agent_id):
        error = "agent_id must be lowercase letters, numbers, and underscores only"
    elif (WORLDS_DIR / level / "agents" / agent_id).exists():
        error = f"Agent '{agent_id}' already exists in {level}"

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
        })

    save_agent(level, agent_id, form)
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
    form = dict(await request.form())
    save_agent(level, agent_id, form)
    return RedirectResponse(f"/worlds/{level}/agents/{agent_id}?saved=1", status_code=303)


@app.post("/worlds/{level}/agents/{agent_id}/delete")
async def delete_agent(level: str, agent_id: str):
    import shutil
    path = WORLDS_DIR / level / "agents" / agent_id
    if path.exists():
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
    return templates.TemplateResponse(request, "sim.html", {"request": request, "runner_url": RUNNER_URL})


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
        mode=body.get("mode", "live"),
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


async def _maybe_json(request: Request) -> dict:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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
