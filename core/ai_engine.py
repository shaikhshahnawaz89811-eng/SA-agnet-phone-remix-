"""
core/ai_engine.py
Groq AI + Offline Module AI -- status markers, engine-priority logic
for Chat Mode (§9, §30), and the Planner Module's status-line
(§25 -- lives inside 'Thinking....', no separate top-level box).

NOTE: This build stage does not call the real Groq HTTP API or a real
local Ollama model -- that needs the user's own Termux + network +
API keys, which this container doesn't have. The state machine,
priority logic, and status text match spec exactly; wire the real
HTTP call into `_call_groq()` / the real Ollama call into
`_call_offline()` when running on-device.
"""
from core import data_store as ds
from core.ai_clients import GroqClient, OfflineAIClient, RateLimitError


class AIEngineStatus:
    def __init__(self, credential_store):
        self.creds = credential_store
        self.offline_client = OfflineAIClient()
        self.state = ds.load("ai_status", {
            "groq": {"status": "Idle", "pct": 0, "project": "", "file": ""},
            "offline": {"status": "Idle", "pct": 0},
        })

    def _save(self):
        ds.save("ai_status", self.state)

    def groq_line(self):
        g = self.state["groq"]
        if g["status"] == "Idle":
            return "Groq AI: Idle 0% -- Engine free hai"
        loc = f" (Proj: {g['project']} / {g['file']})" if g.get("project") else ""
        return f"Groq AI: {g['status']}.... {g['pct']}%{loc}"

    def offline_line(self):
        o = self.state["offline"]
        return f"Offline Module AI: {o['status']}.... {o['pct']}%"

    def pick_engine(self):
        """[v9] Final engine-priority logic for Chat Mode:
        1. Offline tried first by default.
        2. Offline free -> Offline handles it, Groq untouched.
        3. Offline busy -> check Groq; whichever is free FIRST gets it.
        No user wait/choose."""
        if self.state["offline"]["status"] == "Idle":
            return "offline"
        if self.state["groq"]["status"] == "Idle":
            if self.creds.get("groq_api_key"):
                return "groq"
            return None  # both effectively unavailable -- Msg Box should ask for key
        return None  # both busy

    def set_thinking(self, engine, project="", sub_task_label="", sub_task_idx=None, sub_task_total=None):
        """Planner Module status line lives inside Thinking (§25):
        'Planning: Sub-task 2/5 -- <naam> -- 0%' (v19 granular)."""
        if sub_task_idx is not None:
            label = f"Planning: Sub-task {sub_task_idx}/{sub_task_total} -- {sub_task_label} -- 0%"
        else:
            label = "Thinking...."
        self.state[engine]["status"] = label if sub_task_idx is not None else "Thinking"
        self.state[engine]["pct"] = 0
        if engine == "groq":
            self.state["groq"]["project"] = project
        self._save()

    def set_coding(self, engine, pct, project="", file=""):
        self.state[engine]["status"] = "Coding"
        self.state[engine]["pct"] = pct
        if engine == "groq":
            self.state["groq"]["project"] = project
            self.state["groq"]["file"] = file
        self._save()

    def set_idle(self, engine):
        self.state[engine]["status"] = "Idle"
        self.state[engine]["pct"] = 0
        self._save()

    def generate(self, engine, system_prompt, user_prompt):
        """REAL call to the chosen engine. Returns (ok, text_or_message).
        Never raises -- network/key problems become the exact status
        text the spec expects instead of a crash."""
        if engine == "groq":
            key = self.creds.get("groq_api_key")
            if not key:
                return False, "Groq API key missing -- Msg Box me maanga jaa raha hai."
            try:
                text = GroqClient(key).generate(system_prompt, user_prompt)
                return True, text
            except RateLimitError:
                return False, "Groq rate-limited (429) -- Offline AI try karein."
            except Exception as e:
                return False, f"Groq call fail hui: {e}"
        elif engine == "offline":
            if not self.offline_client.is_reachable():
                return False, ("Offline Module AI (local Ollama) is device par reachable nahi hai -- "
                                "`ollama serve` chala kar 'ollama pull qwen2.5-coder:7b' karein.")
            try:
                text = self.offline_client.generate(f"{system_prompt}\n\n{user_prompt}")
                return True, text
            except Exception as e:
                return False, f"Offline AI call fail hui: {e}"
        return False, "Unknown engine."


CHAT_STATUS_MARKERS = [
    "Routing...", "Queued -- engine busy", "Loading project context...",
    "Scanning project...", "Thinking...", "Searching...", "Validating...",
    "Pushing...", "Pending -- remote verify in progress", "Done",
]


class SearchAPIRouter:
    """Web Search API -- Groq uses Tavily by default, Offline uses
    Serper.dev by default; on 429 (limit) fall back to the other
    engine's key. If both exhausted: skip search, proceed on existing
    knowledge, status: 'Search: unavailable (both keys exhausted) --
    proceeding without web search' (§31, v15)."""

    def __init__(self, credential_store):
        self.creds = credential_store

    def pick_key(self, primary_engine):
        primary_field = "tavily_api_key" if primary_engine == "groq" else "serper_api_key"
        fallback_field = "serper_api_key" if primary_engine == "groq" else "tavily_api_key"
        if self.creds.get(primary_field):
            return primary_field
        if self.creds.get(fallback_field):
            return fallback_field
        return None

    def status_line(self, primary_engine):
        key = self.pick_key(primary_engine)
        if key:
            return f"Search: using {key}"
        return "Search: unavailable (both keys exhausted) -- proceeding without web search"
