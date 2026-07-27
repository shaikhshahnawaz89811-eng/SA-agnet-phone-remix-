"""
core/projects.py
Project Storage -- Create / All Projects / Delete, with the exact
guard/cleanup behavior from §5-§29 of the spec.
"""
import difflib
from core import data_store as ds


class ProjectManager:
    def __init__(self, msgbox, git_engine, blueprint_store, task_monitor):
        self.state = ds.load("projects", {"projects": {}})
        self.msgbox = msgbox
        self.git = git_engine
        self.blueprint = blueprint_store
        self.task_monitor = task_monitor

    def _save(self):
        ds.save("projects", self.state)

    # ---- Create (§5-§8) ---------------------------------------------------
    def exists(self, name):
        return name in self.state["projects"]

    def create(self, name, source_type, languages=None, is_apk=False):
        """source_type: 'github' | 'zip' | 'task' | 'chat'.
        [v15] duplicate/khaali-naam check happens at the call site
        before this is invoked."""
        if not name.strip():
            return False, "Project naam khaali nahi ho sakta."
        if self.exists(name):
            return False, "Yeh project naam pehle se maujood hai."
        self.state["projects"][name] = {
            "name": name,
            "source_type": source_type,
            "languages": languages or [],   # [v18] per-component list, not single field
            "is_apk": is_apk,
            "files_total": 0,
            "files_complete": 0,
            "complete_pct": 0,
            "created": ds.now_iso(),
        }
        self._save()
        ds.project_dir(name)
        return True, "Project created."

    # ---- All Projects (§13-§27) -------------------------------------------
    def all_names(self):
        return list(self.state["projects"].keys())

    def search(self, query):
        """[v15] case-insensitive; exact miss -> closest-match suggestions
        before 'exist nahi karta'."""
        q = query.strip().lower()
        names = self.all_names()
        exact = [n for n in names if n.lower() == q]
        if exact:
            return "exact", exact
        partial = [n for n in names if q in n.lower()]
        if partial:
            return "partial", partial
        close = difflib.get_close_matches(query, names, n=3, cutoff=0.5)
        if close:
            return "suggest", close
        return "none", []

    def rename(self, old_name, new_name):
        if not new_name.strip():
            return False, "Naya naam khaali nahi ho sakta."
        if self.exists(new_name):
            return False, "Yeh naam pehle se kisi aur project ka hai."
        if old_name not in self.state["projects"]:
            return False, "Project not found."
        proj = self.state["projects"].pop(old_name)
        proj["name"] = new_name
        self.state["projects"][new_name] = proj
        self._save()
        # Sync everywhere: Task Monitor / Git rules / Blueprint / not-pushed
        for t in self.task_monitor.state["tasks"]:
            if t["project"] == old_name:
                t["project"] = new_name
        self.task_monitor._save()
        if old_name in self.git.state["rules"]:
            self.git.state["rules"][new_name] = self.git.state["rules"].pop(old_name)
        if old_name in self.git.state["not_pushed"]:
            self.git.state["not_pushed"][new_name] = self.git.state["not_pushed"].pop(old_name)
        self.git._save()
        if old_name in self.blueprint.state:
            self.blueprint.state[new_name] = self.blueprint.state.pop(old_name)
            self.blueprint._save()
        return True, "Renamed and synced across Task Monitor / Git / Blueprint."

    def info(self, name):
        return self.state["projects"].get(name)

    def delete(self, name):
        """Full cleanup chain (§29): Blueprint, Msg Box history, Not Push
        Task, Git Status record, Task Monitor -- all cleaned/stopped, but
        Msg Box Unseen-Guard and Uncommitted-Work Guard archive first."""
        if name not in self.state["projects"]:
            return False, "Project not found.", {}

        archived_msgs = self.msgbox.cleanup_for_project_delete(name)
        archived_uncommitted = self.git.uncommitted_work_guard_on_delete(name)
        self.blueprint.delete(name)
        self.git.cleanup_project(name)
        # Stop any active Task Monitor entries for this project
        for t in self.task_monitor.state["tasks"]:
            if t["project"] == name and t["status"] == "Running":
                t["status"] = "Stopped"
        self.task_monitor._save()
        self.task_monitor.state["tasks"] = [
            t for t in self.task_monitor.state["tasks"] if t["project"] != name
        ]
        self.task_monitor._save()

        del self.state["projects"][name]
        self._save()
        return True, "Deleted.", {
            "archived_msgs": len(archived_msgs),
            "archived_uncommitted": len(archived_uncommitted),
        }
