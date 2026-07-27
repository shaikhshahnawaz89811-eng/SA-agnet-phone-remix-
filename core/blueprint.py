"""
core/blueprint.py
Project Blueprint -- Add / Edit / Delete(password) / Show(organised,
per-sub-task, v19) / Export to PDF(v16) (§18).
"""
from core import data_store as ds


class BlueprintStore:
    def __init__(self):
        self.state = ds.load("blueprints", {})  # project -> {sub_tasks:[...], status}

    def _save(self):
        ds.save("blueprints", self.state)

    def _proj(self, project):
        return self.state.setdefault(project, {"sub_tasks": [], "status": "Draft"})

    def add(self, project, text):
        bp = self._proj(project)
        sub_id = len(bp["sub_tasks"]) + 1
        bp["sub_tasks"].append({"id": sub_id, "name": text, "status": "Pending"})
        self._save()
        return sub_id

    def edit(self, project, sub_id, new_text, active_write_in_progress=False):
        """[v15] If the AI is actively writing this project's file when
        an edit is attempted, reconcile instead of silently clobbering:
        ask the caller to let the current file finish, then reload."""
        if active_write_in_progress:
            return False, ("Current file complete karke naya blueprint "
                            "reload karo -- ab edit apply hoga.")
        bp = self._proj(project)
        for st in bp["sub_tasks"]:
            if st["id"] == sub_id:
                st["name"] = new_text
                self._save()
                return True, "Updated."
        return False, "Sub-task not found."

    def delete(self, project):
        if project in self.state:
            del self.state[project]
            self._save()
        return True

    def show(self, project):
        """[v19] Organised per-sub-task view (name+status), not raw
        plan text."""
        return self._proj(project)["sub_tasks"], self._proj(project)["status"]

    def mark_ready_for_coding(self, project):
        self._proj(project)["status"] = "Ready for Coding"
        self._save()
