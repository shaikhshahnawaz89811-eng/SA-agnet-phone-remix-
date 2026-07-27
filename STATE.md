# SA Agent — Project State (Live Tracking File)

> RULE: Har naya AI session/agent isi file ko SABSE PEHLE padhega, code shuru karne se pehle.
> Har session ke END me isi file ko update karke commit karna hai — purana content delete nahi,
> sirf status update ya "Session Log" me naya entry ADD karna hai (append-only convention).

## 1. Project Overview
- **Naam:** SA Agent
- **Type:** CLI tool (Python)
- **Platform:** Termux (Android/phone) — koi bhi library/command jo Termux me na chale, use mat karo
- **Reference docs:** SA_Agent_Master_Documentation (v9-v27) + rules_updated (Rule 1-21)
- **Goal:** Documentation me likha poora workflow (Menu, Create Project, Chat Mode, Planner, Full Scan & Fix, Route B, etc.) actual code me implement karna

## 2. Environment / Setup Status
- [ ] requirements.txt final hai ya aur dependency chahiye — CHECK KARO
- [ ] .env / API keys (Groq, Tavily, Serper.dev) ka setup flow ready hai ya nahi
- [ ] Termux-specific issue koi hai kya (path, permission, package)

## 3. Module-Wise Status
(Audit Session 2 me poori repo Rule 1-21 ke against manually check ki gayi — 21 files, 1990 lines)

| File | Status | Note |
|---|---|---|
| main.py | 🟡 | Skeleton kaam karta hai; Errors Fix menu stub hai (BUG-6); Git push ke liye remote-set option nahi (BUG-1) |
| core/ai_clients.py | ✅ | Real Groq/Ollama/Tavily/Serper HTTP calls, sahi implement hai |
| core/ai_engine.py | ⚠️ | Kaam karta hai (real Groq call), par docstring galat/purani hai — "stubbed" bolti hai jabki real call hai (BUG-7) |
| core/git_ops.py | 🟡 | Real git subprocess calls sahi; `set_remote()` kabhi call nahi hoti (BUG-1); `push()` branch="main" hardcoded (BUG-2) |
| core/git_engine.py | 🟡 | State/counters sahi; docstring me `_run_git()` ka reference hai jo is file me exist hi nahi karta (BUG-7) |
| core/data_store.py | ✅ | Atomic JSON write, safe load, sahi hai |
| core/msgbox.py | ⚠️ | `id` = `len()`-based hai, persisted counter nahi — archive ke baad id-collision ho sakta hai (BUG-3) |
| core/task_monitor.py | 🟡 | `stop()` ka `sandbox_mid_validation` kabhi True pass nahi hota — safe-abort feature (§36) dead hai (BUG-4) |
| core/blueprint.py | 🟡 | `edit()` ka `active_write_in_progress` kabhi True pass nahi hota — reconciliation feature (§18) dead hai (BUG-4) |
| core/projects.py | ✅ | Create/Rename/Delete/Search + sync-on-rename + archive-guards sab sahi |
| core/security.py | ✅ | Password/lockout/recovery + Credential Store sahi |
| core/pdf_and_zip.py | ✅ | Real PDF export + real zip extraction, sahi error messages |
| core/scan_engine.py | 🟡 | Syntax-check + dead-code detection sahi; "fixed" list hamesha khaali — auto-clean by-design implement nahi (BUG-8, design-note) |
| core/helpers.py | 🟡 | `ci_workflow_auto_create` sahi wired; `readme_sync`'s structural-update branch kabhi trigger nahi hota (BUG-5) |
| core/ui.py | ✅ | Organised-table/status-bar sahi, spec match karta hai |
| core/__init__.py | ✅ | Khaali init file, issue nahi |

## 4. Completed (confirmed working)
- Password/Security Module (3-attempt lock, recovery code, change/forgot) — full match
- Project Create/Rename/Delete/Search + Archived Msg Box + Archived Uncommitted Work guards
- Real Groq / Offline(Ollama) / Tavily / Serper HTTP clients
- Real PDF export (reportlab) + real zip extraction with correct error text
- Blueprint add/show/mark-ready, Task Monitor add/list/progress
- CI-Workflow Auto-Create (APK projects) — reuse-if-exists logic sahi

## 5. In-Progress / Partial
- Full Scan & Fix — scans + flags dead-code sahi, par kabhi kuch "fix" nahi karta (list hamesha empty)
- Git push flow — kaam karta hai SIRF GitHub-Copy se bane project ke liye (clone se origin auto-set hota hai); Zip/Task/Chat se bane project ka remote kabhi set hi nahi hota

## 6. Not Started
- Errors Fix menu (Main Menu option 6) — koi real functionality nahi, sirf static message
- View Files me "abhi update ho rahi hai" status jab file active AI-write me ho (spec §25/v12 §54)
- Non-Python (Kotlin/XML/Gradle) files ke liye Rule-19 copy-first-validate — abhi sirf Python validate hoti hai

## 7. Known Bugs / Risks (Priority order — delete mat karo, sirf status update karo jab fix ho)
1. **[HIGH][FIXED] BUG-1 — `set_remote()` orphan function.** `core/git_ops.py` me defined hai, par poori codebase me kahin call nahi hoti. Zip/Task/Chat se bana project "Git push change" try karega toh hamesha "remote configure karein" error dega — UI me remote add karne ka option hi nahi. Fix: GitHub Setting menu me "Set/Update Remote URL" option add karke `git_ops.set_remote()` call karo.
2. **[MEDIUM][FIXED] BUG-2 — Push branch hardcoded.** File: `core/git_ops.py` Function: `push()`. `branch="main"` fixed hai. Cloned repo ka default "master" ho to push fail hoga. Fix: push se pehle `git branch --show-current` se actual branch detect karo.
3. **[MEDIUM][FIXED] BUG-3 — MsgBox id collision risk.** File: `core/msgbox.py` Function: `add()`. `msgbox.add()` me id = `len(messages)+len(archived)+1` — persisted counter nahi hai. Archive ke baad do entries same id le sakti hai. Fix: `data_store` me persisted incrementing counter.
4. **[LOW][FIXED] BUG-4 — Do dead parameters. File: `main.py` exact call-sites only. Line 386: `task_monitor.stop(task["id"])` validation failure path hai, yahan `sandbox_mid_validation=True` pass karo. Line 501: `blueprint.edit(...)` me `active_write_in_progress` ko actual AI writing state ke hisaab se pass karo. Line 656: normal stop hai, default False rehne do. IMPORTANT: Do not rewrite full main.py. Make minimal targeted edits only at the listed call-sites. Preserve all existing code. Related: `core/task_monitor.py::stop()` and `core/blueprint.py::edit()`.
5. **[LOW][OPEN] BUG-5 — README structural-update kabhi nahi hota.** `readme_sync(name, structural_change_summary=...)` teeno call-sites me sirf `readme_sync(name)` hi call hota hai. Task complete hone ke baad README kabhi update nahi hota (spec §28).
6. **[LOW][OPEN] BUG-6 — Errors Fix menu stub.** Main Menu option 6 sirf static line print karta hai. `scan_engine.py` ka real `error_pending` data yahan surface nahi hota (spec §32).
7. **[LOW][OPEN] BUG-7 — Stale/galat docstrings.** `ai_engine.py` header "stubbed" bolta hai jabki real Groq call ho rahi hai; `git_engine.py` header `_run_git()` reference karta hai jo file me exist hi nahi karta.
8. **[DESIGN NOTE, not a bug] BUG-8 — Full Scan & Fix kabhi auto-clean nahi karta.** `scan_engine.py` deliberately sirf FLAG karta hai (docstring me hi likha hai), kabhi delete nahi. Spec §23 se safe-side intentional deviation — bug nahi, sirf note.
9. **[LOW][OPEN] GAP-1 — View Files me active-write status missing** (spec §25/v12 §54) — bilkul implement nahi.

## 8. Next Step (agla session yahi se shuru kare)
1. BUG-1 (Set Remote UI option) — sabse zyada block kar raha hai
2. BUG-2 (branch auto-detect)
3. BUG-3 (persisted id counter)
4. BUG-4 aur BUG-5 — wire karo ya Rule 6 ke hisaab se explicitly hata do, undecided mat chhodo
5. BUG-6 — Errors Fix ko scan_engine se connect karo

## 9. Session Log (append-only, purana kabhi mat hatao)
- **[2026-07-28 01:40]** — BUG-3 fixed by agent_runner.py (provider: groq), committed to git.
- **[2026-07-28 01:35]** — BUG-2 fixed by agent_runner.py (provider: groq), committed to git.
- **[2026-07-28 01:09]** — BUG-1 fixed by agent_runner.py (provider: groq), committed to git.
- **[Session 1]** — Zip upload hua, initial structure review hua. STATE.md banaya gaya.
- **[Session 2]** — Poora audit hua: Master Documentation PDF + rules_updated PDF + zip ka poora code (21 files) Rule 1-21 ke against manually cross-check kiya gaya. 9 findings mile (BUG-1 se BUG-8 + GAP-1), priority order me list kiye gaye. Koi fix abhi apply nahi hua — sirf audit.

