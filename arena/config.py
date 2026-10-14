"""arena.toml: optional endpoints / extra engines. Secrets via env vars only."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {"timeouts": {"base_s": 120, "per_page_s": 30}, "engines": {}}


def load(path: Path | None = None) -> dict:
    path = path or ROOT / "arena.toml"
    cfg = {**DEFAULTS}
    if path.exists():
        user = tomllib.loads(path.read_text())
        cfg["timeouts"] = {**DEFAULTS["timeouts"], **user.get("timeouts", {})}
        cfg["engines"] = user.get("engines", {})
    return cfg
