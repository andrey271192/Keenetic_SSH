import os, json, logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("keenetic_ssh")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SSH_USER = os.getenv("SSH_USER", "root")
SSH_PASS = os.getenv("SSH_PASS", "keenetic")

ROUTERS_FILE = DATA_DIR / "routers.json"

def ensure_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ROUTERS_FILE.exists():
        ROUTERS_FILE.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

ensure_data()
