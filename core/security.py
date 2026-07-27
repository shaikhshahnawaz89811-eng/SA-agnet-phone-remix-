"""
core/security.py
Password/Security Module (Addendum 15/v13/v20) + API Key Credential
Persistence (Addendum 20/v17, updated v26 with 'Clear Key').

Every password-check point (Delete Project, Rename, Delete Blueprint,
Task Monitor Delete) calls PasswordManager.verify() so the 3-attempt /
24-hour-lock behavior is identical everywhere, per spec §22.
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from core import data_store as ds

MAX_ATTEMPTS = 3
LOCK_HOURS = 24


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


class PasswordManager:
    def __init__(self):
        self.state = ds.load("security", {
            "password_hash": None,
            "recovery_code_hash": None,
            "failed_attempts": 0,
            "locked_until": None,
        })

    def _save(self):
        ds.save("security", self.state)

    def is_set(self) -> bool:
        return bool(self.state.get("password_hash"))

    def create_password(self, pw: str) -> str:
        """First-run password create. Returns the plaintext recovery code
        (shown once — offline/no-email context, so this IS the recovery
        channel, per §22)."""
        self.state["password_hash"] = _hash(pw)
        recovery_code = secrets.token_hex(4).upper()  # e.g. 'A1B2C3D4'
        self.state["recovery_code_hash"] = _hash(recovery_code)
        self.state["failed_attempts"] = 0
        self.state["locked_until"] = None
        self._save()
        return recovery_code

    def change_password(self, old_pw: str, new_pw: str):
        ok, msg = self.verify(old_pw)
        if not ok:
            return False, msg
        self.state["password_hash"] = _hash(new_pw)
        self._save()
        return True, "Password changed."

    def reset_with_recovery_code(self, recovery_code: str, new_pw: str):
        if _hash(recovery_code.strip().upper()) != self.state.get("recovery_code_hash"):
            return False, "Recovery code galat hai."
        self.state["password_hash"] = _hash(new_pw)
        self.state["failed_attempts"] = 0
        self.state["locked_until"] = None
        self._save()
        return True, "Password reset ho gaya."

    def locked(self):
        lu = self.state.get("locked_until")
        if not lu:
            return False, None
        until = datetime.fromisoformat(lu)
        if datetime.now() < until:
            return True, until
        # Lock window expired — auto-clear
        self.state["locked_until"] = None
        self.state["failed_attempts"] = 0
        self._save()
        return False, None

    def verify(self, pw: str):
        """Returns (ok: bool, message: str). Shared by every
        password-check point in the app (Delete Project, Rename,
        Blueprint Delete, Task Monitor Delete — §22)."""
        is_locked, until = self.locked()
        if is_locked:
            return False, f"Locked hai 3 galat attempts ke baad. Try again after {until.strftime('%Y-%m-%d %H:%M')}."
        if not self.is_set():
            return False, "Koi password set nahi hai — pehle setup karein."
        if _hash(pw) == self.state["password_hash"]:
            self.state["failed_attempts"] = 0
            self._save()
            return True, "OK"
        self.state["failed_attempts"] = self.state.get("failed_attempts", 0) + 1
        if self.state["failed_attempts"] >= MAX_ATTEMPTS:
            self.state["locked_until"] = (datetime.now() + timedelta(hours=LOCK_HOURS)).isoformat()
            self._save()
            return False, f"Wrong password. 3 galat attempts — 24hr ke liye lock ho gaya."
        self._save()
        remaining = MAX_ATTEMPTS - self.state["failed_attempts"]
        return False, f"Wrong password. {remaining} attempt(s) baaki hai."


class CredentialStore:
    """Persistent local file (working-directory) storage for Groq /
    Tavily / Serper.dev keys — loaded automatically on every restart,
    masked on screen, never shown in full (Addendum 20 / v26)."""

    FIELDS = ["groq_api_key", "tavily_api_key", "serper_api_key"]

    def __init__(self):
        self.state = ds.load("credentials", {})

    def _save(self):
        ds.save("credentials", self.state)

    def is_complete(self):
        return all(self.state.get(f) for f in self.FIELDS)

    def missing(self):
        return [f for f in self.FIELDS if not self.state.get(f)]

    def set_key(self, field, value):
        if field not in self.FIELDS:
            raise ValueError(field)
        self.state[field] = value
        self._save()

    def clear_key(self, field):
        """[v26] Settings -> 'Clear Key' -- explicit standalone delete."""
        if field in self.state:
            del self.state[field]
            self._save()

    def masked(self, field):
        val = self.state.get(field)
        if not val:
            return "(not set)"
        if len(val) <= 4:
            return "*" * len(val)
        return "*" * (len(val) - 4) + val[-4:]

    def get(self, field):
        return self.state.get(field)
