# SA Agent — Complete Build (matches SA_Agent_Master_Documentation_Final.pdf)

## Run
```
pip install -r requirements.txt
python3 main.py
```
Pure stdlib + `requests` (HTTP) + `reportlab` (real PDF export). Termux: `pkg install python git`.

## Fully REAL and working (tested)
- Full numbered menu tree exactly per spec (Main Menu 1-9, Create Project,
  All Projects, Project sub-menu, GitHub Setting, Blueprint, Task Monitor)
- Password module: create/verify, 3-attempt / 24-hour lockout — shared
  across Delete Project / Rename / Blueprint Delete / Task Monitor Delete
- Settings ('keys' from Main Menu): Update/Clear API Keys, masked display,
  restart-safe JSON persistence, only prompted once on first run
- Msg Box + Archived Msg Box (Unseen/Unanswered Content Guard)
- Not Push Task + Archived Uncommitted Work (Uncommitted-Work Guard)
- Delete Project full cleanup chain with both guards
- Rename Project with cross-module sync (Task Monitor / Git rules / Blueprint)
- Blueprint per-sub-task store, GitHub rules (duplicate-check, mid-push delay)
- Search by name (case-insensitive, closest-match suggestions)
- REAL `git clone` for GitHub Copy (exact spec error message on bad/private link)
- REAL zip extraction for Zip import (exact spec error message on corrupt/
  password-protected zip)
- REAL per-component language/tech detection (file-extension scan) — not
  a single field, per v18
- REAL `git init/add/commit/push` from GitHub Setting > Git push change,
  with pre-push reconcile (auto-commits dirty state first, v17)
- REAL Full Project Scan & Fix: `py_compile` syntax-check + AST-based
  dead-code candidate detection (unused imports / never-referenced
  top-level functions) for Python files — organised per-file report,
  never silently auto-deletes (flags for review only, per §30 safety rule)
- REAL PDF export (reportlab) for Details / Blueprint / Scan Report —
  actual valid PDF files written to each project's `Exports/` folder
- REAL Groq API calls (needs your Groq key, set via `keys`) and REAL
  local-Ollama calls for Offline AI (needs `ollama serve` +
  `ollama pull qwen2.5-coder:7b` running on your device) — Chat Mode and
  Project > Task both use these; on failure you get the exact honest
  status text (missing key / rate-limited / Ollama unreachable), never a
  fake success
- AI file-writing: parses `### FILE: path` blocks from the AI's reply and
  writes them into the project folder
- CI-Workflow Auto-Create + README Sync Helper (real files written)

## What still needs YOUR device/keys to do anything (code is real, not stubbed)
- Groq replies — need `keys` > Update > your real Groq API key + internet
- Offline AI replies — need Ollama running locally with the 7B model pulled
- `git push` — needs a real GitHub remote + your credentials configured on
  the device (SSH key or credential helper) + internet
- Tavily/Serper web search inside AI answers — needs those keys (wired in
  `core/ai_clients.py`, not yet called from the chat/task flow's prompt —
  add a `search_router.search(...)` call before building the prompt if you
  want live web results injected)
- Route B (GitHub Actions remote-build polling) — not yet built; would
  need a GitHub token + `requests` calls to the Actions API, same pattern
  as `core/git_ops.py`

## Removed from the original zip
`legacy_v35_unused/`, and the old `main.py` / `core/menus.py` /
`core/terminal.py` / `ai/` / `git/` / `build/` / `utils/` — these belonged
to a different, free-text conversational agent architecture (v2) that does
not match the PDF's numbered-menu spec.
