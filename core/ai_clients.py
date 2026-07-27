"""
core/ai_clients.py
REAL network clients -- Groq (cloud), Offline (local Ollama), and the
two Web-Search APIs (Tavily / Serper.dev). These make actual HTTP
calls; they only need your API keys (Groq/Tavily/Serper) or a running
local Ollama server (Offline AI, §24 -- Qwen2.5-Coder-7B/Qwen3-Coder-7B).
No mocking here -- if network/keys aren't available the calls raise
and the caller (core/ai_engine.py) turns that into the correct Msg Box
/ status-bar message per spec, never a silent fake success.
"""
import json
import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:7b"

TAVILY_URL = "https://api.tavily.com/search"
SERPER_URL = "https://google.serper.dev/search"


class GroqClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def generate(self, system_prompt, user_prompt, timeout=60):
        if not self.api_key:
            raise RuntimeError("Groq API key missing.")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 429:
            raise RateLimitError("groq")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class OfflineAIClient:
    """Local Ollama server -- 7B-class coding model (§24). Requires
    Ollama running on-device (`ollama serve` + `ollama pull qwen2.5-coder:7b`)."""

    def __init__(self, base_url=OLLAMA_URL, model=OLLAMA_MODEL):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt, timeout=120):
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        resp = requests.post(self.base_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")

    def is_reachable(self):
        try:
            requests.get(self.base_url.replace("/api/generate", ""), timeout=3)
            return True
        except requests.RequestException:
            return False


class RateLimitError(Exception):
    def __init__(self, engine):
        self.engine = engine
        super().__init__(f"{engine} rate-limited (429)")


class SearchClients:
    """Tavily (Groq default) / Serper.dev (Offline default) with
    fallback-to-other's-key on 429, per §31."""

    def __init__(self, tavily_key, serper_key):
        self.tavily_key = tavily_key
        self.serper_key = serper_key

    def tavily(self, query, timeout=20):
        if not self.tavily_key:
            raise RuntimeError("Tavily key missing.")
        resp = requests.post(
            TAVILY_URL,
            json={"api_key": self.tavily_key, "query": query, "max_results": 5},
            timeout=timeout,
        )
        if resp.status_code == 429:
            raise RateLimitError("tavily")
        resp.raise_for_status()
        return resp.json().get("results", [])

    def serper(self, query, timeout=20):
        if not self.serper_key:
            raise RuntimeError("Serper key missing.")
        headers = {"X-API-KEY": self.serper_key, "Content-Type": "application/json"}
        resp = requests.post(SERPER_URL, headers=headers, json={"q": query}, timeout=timeout)
        if resp.status_code == 429:
            raise RateLimitError("serper")
        resp.raise_for_status()
        return resp.json().get("organic", [])

    def search(self, query, primary_engine):
        """primary_engine: 'groq' (Tavily) or 'offline' (Serper).
        Falls back to the other key on 429; if both exhausted/missing,
        returns (None, status_message) instead of raising, so callers
        can proceed on existing knowledge per §31 v15."""
        order = [self.tavily, self.serper] if primary_engine == "groq" else [self.serper, self.tavily]
        last_err = None
        for fn in order:
            try:
                return fn(query), "ok"
            except RateLimitError:
                last_err = "rate-limited"
                continue
            except RuntimeError:
                last_err = "key-missing"
                continue
        return None, "Search: unavailable (both keys exhausted) -- proceeding without web search"
