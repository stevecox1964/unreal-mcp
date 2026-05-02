from __future__ import annotations

import file_manager as fm
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import MemoryContent, StateContent, TextContent, ToolsContent

app = FastAPI(title="NPC Builder API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


@app.get("/agents")
def list_agents():
    return {"agents": fm.list_agents()}


@app.post("/agents/{agent_id}", status_code=201)
def create_agent(agent_id: str):
    fm.create_agent(agent_id)
    return {"status": "created", "agent_id": agent_id}


@app.delete("/agents/{agent_id}")
def delete_agent(agent_id: str):
    fm.delete_agent(agent_id)
    return {"status": "deleted", "agent_id": agent_id}


# ---------------------------------------------------------------------------
# Text files: character, goals, rules
# ---------------------------------------------------------------------------


@app.get("/agents/{agent_id}/character")
def get_character(agent_id: str):
    return {"content": fm.read_text(agent_id, "character.md")}


@app.put("/agents/{agent_id}/character")
def put_character(agent_id: str, body: TextContent):
    fm.write_text(agent_id, "character.md", body.content)
    return {"status": "saved"}


@app.get("/agents/{agent_id}/goals")
def get_goals(agent_id: str):
    return {"content": fm.read_text(agent_id, "goals.md")}


@app.put("/agents/{agent_id}/goals")
def put_goals(agent_id: str, body: TextContent):
    fm.write_text(agent_id, "goals.md", body.content)
    return {"status": "saved"}


@app.get("/agents/{agent_id}/rules")
def get_rules(agent_id: str):
    return {"content": fm.read_text(agent_id, "rules.md")}


@app.put("/agents/{agent_id}/rules")
def put_rules(agent_id: str, body: TextContent):
    fm.write_text(agent_id, "rules.md", body.content)
    return {"status": "saved"}


# ---------------------------------------------------------------------------
# JSON files: tools, state, memory
# ---------------------------------------------------------------------------


@app.get("/agents/{agent_id}/tools")
def get_tools(agent_id: str):
    return fm.read_json(agent_id, "tools.json")


@app.put("/agents/{agent_id}/tools")
def put_tools(agent_id: str, body: ToolsContent):
    fm.write_json(agent_id, "tools.json", body.model_dump())
    return {"status": "saved"}


@app.get("/agents/{agent_id}/state")
def get_state(agent_id: str):
    return fm.read_json(agent_id, "state.json")


@app.put("/agents/{agent_id}/state")
def put_state(agent_id: str, body: StateContent):
    fm.write_json(agent_id, "state.json", body.model_dump())
    return {"status": "saved"}


@app.get("/agents/{agent_id}/memory")
def get_memory(agent_id: str):
    return fm.read_json(agent_id, "memory.json")


@app.put("/agents/{agent_id}/memory")
def put_memory(agent_id: str, body: MemoryContent):
    fm.write_json(agent_id, "memory.json", body.model_dump())
    return {"status": "saved"}
