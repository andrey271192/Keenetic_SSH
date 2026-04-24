import json, logging
from pathlib import Path
logger = logging.getLogger("keenetic_ssh")

def load_json(path: Path, default=None):
    if default is None: default = {}
    if not isinstance(path, Path): path = Path(path)
    try:
        if path.exists():
            t = path.read_text(encoding="utf-8")
            if t.strip(): return json.loads(t)
        return default
    except Exception as e:
        logger.error(f"load_json {path}: {e}")
        return default

def save_json(path: Path, data):
    if not isinstance(path, Path): path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
