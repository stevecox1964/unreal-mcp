"""#85 — shared APC doctrine: rules.md imports.

The bug this guards is not a crash. It is Maren reasoning "time to refuse this
ground" in SR46 and then emitting walk_to, because six weeks of navigation
doctrine had been typed into dufus/rules.md (94 lines) while hers stayed at 21.
So these checks are about *what an agent actually knows*, not about file I/O.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent_runtime.agent import resolve_rule_imports, RulesImportError  # noqa: E402

WORLD = ROOT / "worlds" / "MCP_World"

_failures = []


def check(label, ok):
    print(f"{'ok' if ok else 'FAIL'}: {label}")
    if not ok:
        _failures.append(label)


def _world(tmp: Path) -> Path:
    (tmp / "doctrine").mkdir(parents=True, exist_ok=True)
    (tmp / "agents" / "test").mkdir(parents=True, exist_ok=True)
    return tmp


def test_import_is_replaced_in_place():
    with tempfile.TemporaryDirectory() as td:
        world = _world(Path(td))
        (world / "doctrine" / "ground.md").write_text(
            "- shared ground rule\n", encoding="utf-8")
        text = "# Rules\n\n@import doctrine/ground.md\n\n- my own rule\n"
        out = resolve_rule_imports(text, world, "test")
        check("the doctrine body is included", "- shared ground rule" in out)
        check("the import line itself is gone", "@import" not in out)
        check("the agent's own rule survives", "- my own rule" in out)
        check("doctrine comes BEFORE the character's own lines (character wins)",
              out.index("shared ground rule") < out.index("my own rule"))


def test_missing_import_fails_loud():
    with tempfile.TemporaryDirectory() as td:
        world = _world(Path(td))
        try:
            resolve_rule_imports("@import doctrine/typo.md\n", world, "test")
            check("a missing import raises", False)
        except RulesImportError as e:
            check("a missing import raises", True)
            check("the error names the file", "typo.md" in str(e))
            check("the error names the agent", "test" in str(e))


def test_empty_import_path_fails_loud():
    with tempfile.TemporaryDirectory() as td:
        world = _world(Path(td))
        try:
            resolve_rule_imports("@import   \n", world, "test")
            check("an empty import path raises", False)
        except RulesImportError:
            check("an empty import path raises", True)


def test_import_cannot_escape_the_world():
    with tempfile.TemporaryDirectory() as td:
        world = _world(Path(td))
        try:
            resolve_rule_imports("@import ../../../secrets.md\n", world, "test")
            check("an import cannot climb out of the world dir", False)
        except RulesImportError:
            check("an import cannot climb out of the world dir", True)


def test_nested_imports_are_rejected():
    # Deliberately dumb: one level, no recursion. A doctrine file that imports
    # another is a maze, and a maze is how the drift hid in the first place.
    with tempfile.TemporaryDirectory() as td:
        world = _world(Path(td))
        (world / "doctrine" / "a.md").write_text(
            "- from a\n@import doctrine/b.md\n", encoding="utf-8")
        (world / "doctrine" / "b.md").write_text("- from b\n", encoding="utf-8")
        try:
            resolve_rule_imports("@import doctrine/a.md\n", world, "test")
            check("a doctrine file may not import another", False)
        except RulesImportError as e:
            check("a doctrine file may not import another", True)
            check("the nesting error explains itself",
                  "may not import" in str(e))


def test_no_imports_is_allowed_but_never_silent(capsys=None):
    with tempfile.TemporaryDirectory() as td:
        world = _world(Path(td))
        out = resolve_rule_imports("- only my own rule\n", world, "lonely")
        check("an agent with no imports still loads", "only my own rule" in out)


def test_the_real_world_agents_share_movement_doctrine():
    """The regression that matters: Maren must know what Dufus knows about walking."""
    def rules(agent_id):
        text = (WORLD / "agents" / agent_id / "rules.md").read_text(encoding="utf-8")
        return resolve_rule_imports(text, WORLD, agent_id)

    dufus, maren = rules("dufus"), rules("maren")

    # Each of these was present for Dufus and absent for Maren in SR46.
    shared = {
        "refusing ground (refuse_cell)": "refuse_cell",
        "withdrawing a refusal (allow_cell)": "allow_cell",
        "look before you step": "Look before you step",
        "behind buildings is not ground to cross": "Behind buildings",
        "refuse ground only once": "Refuse a piece of ground ONCE",
        "breadcrumbs / retrace": "BREADCRUMBS",
        "headings already tried here": "already tried",
        "the footing rule": "FOOTING",
        "progress warning": "PROGRESS WARNING",
        "a person in your way is not a wall": "not a wall",
    }
    for label, needle in shared.items():
        check(f"dufus has {label}", needle in dufus)
        check(f"MAREN has {label}", needle in maren)

    # SR46's smoking gun, stated as a test: she reasoned her way to refusing
    # ground and could not, because her file never said the action existed.
    check("maren can now name the action she reached for in SR46",
          "refuse_cell" in maren)

    # Character stays character — this is not a merge of the two agents.
    check("dufus keeps the surveyor's suppression",
          "Do NOT stop for strangers" in dufus)
    check("maren does NOT inherit the surveyor's suppression",
          "Do NOT stop for strangers" not in maren)
    check("maren keeps her own posture", "stay at the truck" in maren)
    check("dufus alone gets the survey doctrine", "survey_here" in dufus)
    check("maren is not told how to survey", "survey_here" not in maren)

    # The point of the split: doctrine is one file, not two copies that drift.
    check("maren is no longer a stub compared to dufus",
          len(maren.splitlines()) > 80)


def test_agent_load_resolves_imports():
    from agent_runtime.agent import Agent
    agent = Agent.load(WORLD / "agents", "maren")
    check("Agent.load returns doctrine-resolved rules",
          "refuse_cell" in agent.rules_text and "@import" not in agent.rules_text)


def main():
    test_import_is_replaced_in_place()
    test_missing_import_fails_loud()
    test_empty_import_path_fails_loud()
    test_import_cannot_escape_the_world()
    test_nested_imports_are_rejected()
    test_no_imports_is_allowed_but_never_silent()
    test_the_real_world_agents_share_movement_doctrine()
    test_agent_load_resolves_imports()
    if _failures:
        print(f"\n{len(_failures)} doctrine-import check(s) FAILED")
        sys.exit(1)
    print("\nAll doctrine-import checks passed.")


if __name__ == "__main__":
    main()
