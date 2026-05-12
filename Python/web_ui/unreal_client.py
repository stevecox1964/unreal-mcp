"""Thin synchronous Unreal socket client for the web UI."""

import json
import socket

UNREAL_HOST = "127.0.0.1"
UNREAL_PORT = 55557


def _send(command: str, params: dict = None, timeout: float = 3.0):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((UNREAL_HOST, UNREAL_PORT))
        sock.sendall(json.dumps({"type": command, "params": params or {}}).encode("utf-8"))
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                return json.loads(b"".join(chunks).decode("utf-8"))
            except json.JSONDecodeError:
                pass
        return None
    except Exception:
        return None
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def _unwrap(result: dict, key: str):
    """Handle both flat and nested {status,result} response shapes."""
    if not result:
        return None
    if key in result:
        return result[key]
    inner = result.get("result")
    if isinstance(inner, dict) and key in inner:
        return inner[key]
    return None


def get_current_level() -> str | None:
    return _unwrap(_send("get_current_level_name"), "name")


def get_actors() -> list[dict]:
    """Return list of {name, label, class} dicts for all actors in the current level."""
    actors = _unwrap(_send("get_actors_in_level"), "actors")
    return actors if isinstance(actors, list) else []
