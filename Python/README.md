# Unreal MCP

Python bridge for interacting with Unreal Engine 5.5 using the Model Context Protocol (MCP).

## Setup

1. Make sure Python 3.10+ is installed
2. Install `uv` if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Create and activate a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```
4. Install dependencies:
   ```bash
   uv pip install -e .
   ```

At this point, you can configure your MCP Client (Claude Desktop, Cursor, Windsurf) to use the Unreal MCP Server as per the [Configuring your MCP Client](README.md#configuring-your-mcp-client).

## Testing Scripts

Two kinds of scripts live in the [scripts](./scripts) folder:

- **Offline agent-runtime tests** (`scripts/agent_runtime/test_*.py`) stub Unreal entirely â€” no
  editor, no network, no LLM. Run the whole suite with one PASS/FAIL signal:
  ```bash
  .venv/Scripts/python.exe scripts/run_tests.py
  .venv/Scripts/python.exe scripts/run_tests.py --only test_place_resolver   # a single test
  ```
- **Integration demos** (`scripts/{actors,node,blueprints}/*.py`) talk to the Unreal Bridge over a
  direct socket, so they need the editor running in PIE. These are excluded from `run_tests.py`.

You should make sure you have installed dependencies and/or are running in the `uv` virtual environment in order for the scripts to work.


## Troubleshooting

- Make sure Unreal Engine editor is loaded loaded and running before running the server.
- Check logs in `unreal_mcp.log` for detailed error information

## Development

To add new tools, add a command handler to `agent_runtime/unreal_bridge.py` (`UnrealBridge`), then call it from the `AgentManager` action set or expose it through the sim runner's control API (`sim_runner.py`) as appropriate.