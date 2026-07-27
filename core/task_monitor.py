"""
core/task_monitor.py
Task Monitor -- live task list (project+%), Stop/Continue/Delete,
all-project or specific-project scope (§36).
"""
from core import data_store as ds


class TaskMonitor:
    def __init__(self):
        self.state = ds.load("task_monitor", {"tasks": []})

    def _save(self):
        ds.save("task_monitor", self.state)

    def add_task(self, project, description):
        t = {
            "id": len(self.state["tasks"]) + 1,
            "project": project,
            "description": description,
            "status": "Running",   # Running / Stopped / Done
            "progress": 0,
            "created": ds.now_iso(),
        }
        self.state["tasks"].append(t)
        self._save()
        return t

    def list_tasks(self, project=None):
        tasks = self.state["tasks"]
        if project:
            tasks = [t for t in tasks if t["project"] == project]
        return tasks

    def set_progress(self, task_id, pct):
        for t in self.state["tasks"]:
            if t["id"] == task_id:
                t["progress"] = pct
                if pct >= 100:
                    t["status"] = "Done"
        self._save()

    def stop(self, task_id, sandbox_mid_validation=False):
        for t in self.state["tasks"]:
            if t["id"] == task_id:
                t["status"] = "Stopped"
                if sandbox_mid_validation:
                    # [v15] safe-abort + sandbox reset
                    return "Stopped -- validation was incomplete"
        self._save()
        return "Stopped"

    def continue_task(self, task_id):
        for t in self.state["tasks"]:
            if t["id"] == task_id and t["status"] == "Stopped":
                t["status"] = "Running"
        self._save()

    def delete(self, task_id):
        self.state["tasks"] = [t for t in self.state["tasks"] if t["id"] != task_id]
        self._save()
