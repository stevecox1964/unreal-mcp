from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("AgentRuntime")


class MemoryStore:
    def __init__(self, worlds_dir: Path):
        self.worlds_dir = worlds_dir
        self.agents_dir: Path | None = None
        self.decisions_log: Path | None = None
        self.events_log: Path | None = None
        # Current sim run tag (SR<n>), set by AgentManager at run start so each
        # decision-log entry is attributable to a single run.
        self.sim_run_id: str = "SR0"

    def update_agents_dir(self, agents_dir: Path) -> None:
        self.agents_dir = agents_dir
        log_dir = agents_dir.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_log = log_dir / "agent_decisions.log"
        self.events_log = log_dir / "world_events.log"

    # ── Read ──────────────────────────────────────────────────────────────────

    def load_memories(self, agent_id: str) -> list[dict]:
        if not self.agents_dir:
            return []
        p = self.agents_dir / agent_id / "memory.json"
        if not p.exists():
            return []
        raw = json.loads(p.read_text(encoding="utf-8")).get("memories", [])
        # Normalise string seeds → dict so callers can always call .get()
        return [
            m if isinstance(m, dict) else {"timestamp": "1970-01-01T00:00:00+00:00", "importance": 0.5, "text": str(m)}
            for m in raw
        ]

    def get_relevant_memories(self, agent_id: str) -> list[dict]:
        memories = self.load_memories(agent_id)
        high_importance = [m for m in memories if m.get("importance", 0) >= 0.7]
        recent = memories[-5:]
        # Merge, deduplicate by timestamp, sort
        combined = {m["timestamp"]: m for m in high_importance + recent}
        return sorted(combined.values(), key=lambda m: m["timestamp"])

    def get_recent_events(self, limit: int = 20, sim_run_id: str = None) -> list[dict]:
        """Return recent decisions, optionally restricted to one simulation run."""
        if limit <= 0:
            return []
        if not self.decisions_log or not self.decisions_log.exists():
            return []
        lines = self.decisions_log.read_text(encoding="utf-8").strip().splitlines()
        entries = []
        for line in lines:
            try:
                entry = json.loads(line)
                if sim_run_id is None or entry.get("sim_run") == sim_run_id:
                    entries.append(entry)
            except json.JSONDecodeError:
                pass
        return entries[-limit:]

    def clear_recent_events(self) -> int:
        """Empty the decision log (the Sim-page "feed"). Returns lines cleared.

        Truncates ``agent_decisions.log`` rather than deleting it so the path
        stays valid for the next tick. Agent memories (memory.json) are untouched
        — this only clears the debug decision feed.
        """
        if not self.decisions_log or not self.decisions_log.exists():
            return 0
        cleared = len(self.decisions_log.read_text(encoding="utf-8").strip().splitlines())
        self.decisions_log.write_text("", encoding="utf-8")
        return cleared

    # ── Write ─────────────────────────────────────────────────────────────────

    _MAX_MEMORIES = 30

    def reset_memories(self, agent_id: str) -> str:
        """Restore memory.json from memory.seed.json if present, else clear it.

        memory.seed.json holds an agent's hand-authored starting memories so a
        reset doesn't wipe them along with the run-accumulated ones.
        Returns "seeded" or "cleared".
        """
        p = self.agents_dir / agent_id / "memory.json"
        seed = self.agents_dir / agent_id / "memory.seed.json"
        if seed.exists():
            p.write_text(seed.read_text(encoding="utf-8"), encoding="utf-8")
            return "seeded"
        p.write_text(
            json.dumps({"agent_id": agent_id, "memories": []}, indent=2),
            encoding="utf-8",
        )
        return "cleared"

    def record(
        self,
        agent_id: str,
        observation: dict,
        action: dict,
        result: dict,
        memory_update: str | None = None,
        importance: float = 0.5,
        timing: dict | None = None,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = {
            "timestamp": timestamp,
            "sim_run": self.sim_run_id,
            "agent_id": agent_id,
            "action_type": action.get("type"),
            "thought": observation.get("_thought"),
            "result_status": result.get("status") or result.get("success"),
        }
        if timing:
            entry["timing"] = timing
        with open(self.decisions_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Don't persist memories for idle actions — they're never meaningful.
        # Also skip low-importance updates to avoid log spam.
        action_type = action.get("type", "idle")
        if memory_update and action_type != "idle":
            # Normalize: LLM sometimes returns {"text": "..."} instead of a plain string.
            if isinstance(memory_update, dict):
                memory_update = memory_update.get("text", str(memory_update))

            p = self.agents_dir / agent_id / "memory.json"
            data = (
                json.loads(p.read_text(encoding="utf-8"))
                if p.exists()
                else {"agent_id": agent_id, "memories": []}
            )
            data["memories"].append(
                {"timestamp": timestamp, "importance": importance, "text": memory_update}
            )
            # Trim to keep the most recent N entries.
            if len(data["memories"]) > self._MAX_MEMORIES:
                data["memories"] = data["memories"][-self._MAX_MEMORIES:]
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")

        logger.info(
            f"[{agent_id}] action={action.get('type')} "
            f"result={result.get('status', result.get('success', '?'))}"
        )
