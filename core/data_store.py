"""
core/data_store.py
Lightweight JSON persistence — no external DB, Termux-friendly.
Every module below reads/writes through here so state survives
across `python main.py` restarts (Doc v9 §1, Addendum 20 session-recovery).
"""
import json
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
PROJECTS_DIR = os.path.join(ROOT, "projects")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)


def _path(name):
    return os.path.join(DATA_DIR, f"{name}.json")


def load(name, default=None):
    p = _path(name)
    if not os.path.exists(p):
        return default if default is not None else {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupt file — never silent-crash the whole agent, treat as
        # missing so the relevant module can re-init / ask via Msg Box.
        return default if default is not None else {}


def save(name, data):
    p = _path(name)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)  # atomic write — no half-written state files


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def project_dir(project_name):
    d = os.path.join(PROJECTS_DIR, project_name)
    os.makedirs(d, exist_ok=True)
    return d
