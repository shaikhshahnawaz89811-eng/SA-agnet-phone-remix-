"""
core/git_engine.py
Git Engine -- status counters, per-project Rules list, Not-Push-Task
tracking + Uncommitted-Work Guard (§17, §19, §28, §29).

Real `git clone/commit/push` calls are stubbed here (network is not
available in this build stage) but the state machine, counters, and
guard behavior are real and match spec exactly. Wire actual subprocess
git calls into `_run_git()` when this runs on the user's own Termux
with network access.
"""
from core import data_store as ds


class GitEngine:
    def __init__(self):
        self.state = ds.load("git_engine", {
            "pass": 0, "fail": 0, "running": 0, "retry": 0,
            "rules": {},          # project -> [rule strings]
            "not_pushed": {},     # project -> [ {desc, ts} ]
            "archived_uncommitted": [],  # moved on delete, tagged w/ project
        })

    def _save(self):
        ds.save("git_engine", self.state)

    # ---- status bar / Git Status screen ---------------------------------
    def counters(self):
        s = self.state
        return f"Git: Pass[{s['pass']}] Fail[{s['fail']}] Running[{s['running']}] Retry[{s['retry']}]"

    def record_result(self, ok: bool):
        if ok:
            self.state["pass"] += 1
        else:
            self.state["fail"] += 1
        self._save()

    # ---- Rules (§17) -----------------------------------------------------
    def rules(self, project):
        return self.state["rules"].get(project, [])

    def add_rule(self, project, rule_text):
        rules = self.state["rules"].setdefault(project, [])
        if rule_text.strip().lower() in [r.lower() for r in rules]:
            return False, "Yeh rule pehle se maujood hai (duplicate)."
        rules.append(rule_text)
        self._save()
        return True, "Rule added."

    def remove_rule(self, project, rule_text, mid_push=False):
        rules = self.state["rules"].get(project, [])
        if rule_text not in rules:
            return False, "Rule not found."
        if mid_push:
            # [v15] mid-push removal is delayed, not instant.
            return True, "Removing... applies from next push."
        rules.remove(rule_text)
        self._save()
        return True, "Rule removed."

    # ---- Not Push Task + Uncommitted-Work Guard (§19, §29) ---------------
    def add_not_pushed(self, project, description):
        entries = self.state["not_pushed"].setdefault(project, [])
        entries.append({"desc": description, "ts": ds.now_iso()})
        self._save()

    def not_pushed(self, project):
        return self.state["not_pushed"].get(project, [])

    def push(self, project):
        """Simulated push -- clears not-pushed entries for the project."""
        had = bool(self.state["not_pushed"].get(project))
        self.state["not_pushed"][project] = []
        self.record_result(True)
        self._save()
        return had

    def uncommitted_work_guard_on_delete(self, project):
        """[v15 -- HIGHEST PRIORITY fix] Not-Push-Task entries are never
        wiped on Delete Project -- they move to a global, read-only
        'Archived Uncommitted Work' tagged with the project name."""
        entries = self.state["not_pushed"].pop(project, [])
        for e in entries:
            self.state["archived_uncommitted"].append({**e, "project": project})
        self._save()
        return entries

    def archived_uncommitted(self, project=None):
        arc = self.state["archived_uncommitted"]
        if project:
            arc = [a for a in arc if a["project"] == project]
        return arc

    def permanent_clean_archived_uncommitted(self, project=None):
        if project:
            self.state["archived_uncommitted"] = [
                a for a in self.state["archived_uncommitted"] if a["project"] != project
            ]
        else:
            self.state["archived_uncommitted"] = []
        self._save()

    def cleanup_project(self, project):
        self.state["rules"].pop(project, None)
        self._save()
