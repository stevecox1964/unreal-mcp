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
