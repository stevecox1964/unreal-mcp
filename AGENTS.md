# Project guidelines

## Unreal Engine

- Engine version: **Unreal Engine 5.5.4**. Be cautious of deprecated or outdated APIs, includes, and practices.

### Coordinate system

UE uses a Z-up, left-handed coordinate system. Editor axis colors: X red, Y green, Z blue.

- **X**: forward/backward (positive = forward)
- **Y**: left/right (positive = right)
- **Z**: up/down (positive = up)

### Units (SI defaults)

| Quantity | Unit |
| --- | --- |
| Distance / Length | Centimeters (cm) |
| Mass | Kilograms (kg) |
| Time | Minutes, Seconds |
| Angles | Degrees |
| Speed / Velocity | Meters per second (m/s) |
| Temperature | Celsius |
| Force | Newtons (N) |
| Torque | Newton-meters (N·m) |

## Python MCP tools

Applies to any function decorated with `@mcp.tool()` (typically under `Python/**/tools/*.py`):

- Parameter types must not be `Any`, `object`, `Optional[T]`, or `Union[T]`.
- For an optional parameter with a default, use `x: T = None` and handle the default in the body — **not** `x: T | None = None`.
- Every tool must have a docstring with example valid inputs, especially when type hints are sparse.

## User workflow preferences

- Do not create or update session handoffs unless the user explicitly requests a handoff. This preference
  also applies at the end of autonomous or multi-task work; report results directly without spending
  tokens on a handoff.
- Do not write, modify, or execute tests unless the user explicitly asks for tests in the current task.
- During feature implementation, it is acceptable to record a non-executable `TEST-FLAG` describing the
  behavior that should be tested, the expected outcome, important edge cases, the suggested test level or
  file, and whether verification requires offline code, Unreal/PIE, or a model call. A test flag tracks
  future coverage only; it is not a test and must not be reported as completed coverage.
- When tests are explicitly requested, the Sol agent writes or modifies the tests, but does not run them.
  Delegate test execution to a Luna or Terra agent; if neither is available, report that tests were not run
  instead of running them with Sol.
