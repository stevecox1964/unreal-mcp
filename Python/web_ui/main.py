"""NPC Builder — local web UI for managing agents under Python/worlds/."""

import json
import re
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web_ui import unreal_client

BASE_DIR = Path(__file__).parent
WORLDS_DIR = BASE_DIR.parent / "worlds"

app = FastAPI(title="NPC Builder")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    worlds = list_worlds()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "worlds": worlds,
        "world_agents": {w: list_agents(w) for w in worlds},
        "current_level": unreal_client.get_current_level(),
    })



@app.get("/worlds/{level}/agents/new", response_class=HTMLResponse)
async def new_agent_form(request: Request, level: str):
    return templates.TemplateResponse("agent.html", {
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
        return templates.TemplateResponse("agent.html", {
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
    return templates.TemplateResponse("agent.html", {
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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
