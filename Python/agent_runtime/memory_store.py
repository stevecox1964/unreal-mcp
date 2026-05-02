from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("AgentRuntime")


class MemoryStore:
    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self.log_dir = agents_dir.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_log = self.log_dir / "agent_decisions.log"
        self.events_log = self.log_dir / "world_events.log"

    # ── Read ──────────────────────────────────────────────────────────────────

    def load_memories(self, agent_id: str) -> list[dict]:
        p = self.agents_dir / agent_id / "memory.json"
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8")).get("memories", [])

    def get_relevant_memories(self, agent_id: str) -> list[dict]:
        memories = self.load_memories(agent_id)
        high_importance = [m for m in memories if m.get("importance", 0) >= 0.7]
        recent = memories[-5:]
        # Merge, deduplicate by timestamp, sort
        combined = {m["timestamp"]: m for m in high_importance + recent}
        return sorted(combined.values(), key=lambda m: m["timestamp"])

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        if not self.decisions_log.exists():
            return []
        lines = self.decisions_log.read_text(encoding="utf-8").strip().splitlines()
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return entries

    # ── Write ─────────────────────────────────────────────────────────────────

    def record(
        self,
        agent_id: str,
        observation: dict,
        action: dict,
        result: dict,
        memory_update: str | None = None,
        importance: float = 0.5,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = {
            "timestamp": timestamp,
            "agent_id": agent_id,
            "action_type": action.get("type"),
            "thought": observation.get("_thought"),
            "result_status": result.get("status") or result.get("success"),
        }
        with open(self.decisions_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        if memory_update:
            p = self.agents_dir / agent_id / "memory.json"
            data = (
                json.loads(p.read_text(encoding="utf-8"))
                if p.exists()
                else {"agent_id": agent_id, "memories": []}
            )
            data["memories"].append(
                {"timestamp": timestamp, "importance": importance, "text": memory_update}
            )
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")

        logger.info(
            f"[{agent_id}] action={action.get('type')} "
            f"result={result.get('status', result.get('success', '?'))}"
        )
