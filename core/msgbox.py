"""
core/msgbox.py
Msg Box (global + per-project) and Archived Msg Box (§16, §26, §33).

Unseen/Unanswered Content Guard (v13 §60, improved v14 §63): on
project delete, READ/ANSWERED entries clean normally; UNREAD/PENDING
entries are never deleted -- they move to a global, read-only
'Archived Msg Box' tagged with the project name.
"""
from core import data_store as ds


class MsgBox:
    def __init__(self):
        self.state = ds.load("msgbox", {"messages": [], "archived": []})

    def _save(self):
        ds.save("msgbox", self.state)

    def add(self, project, text, needs_reply=False):
        entry = {
            "id": len(self.state["messages"]) + len(self.state["archived"]) + 1,
            "project": project,
            "text": text,
            "needs_reply": needs_reply,
            "read": False,
            "replied": False,
            "created": ds.now_iso(),
        }
        self.state["messages"].append(entry)
        self._save()
        return entry

    def all_pending(self, project=None):
        msgs = self.state["messages"]
        if project:
            msgs = [m for m in msgs if m["project"] == project]
        return msgs

    def mark_read(self, msg_id):
        for m in self.state["messages"]:
            if m["id"] == msg_id:
                m["read"] = True
        self._save()

    def reply(self, msg_id, reply_text):
        for m in self.state["messages"]:
            if m["id"] == msg_id:
                m["read"] = True
                m["replied"] = True
                m["reply_text"] = reply_text
        self._save()

    def archived(self, project=None):
        arc = self.state["archived"]
        if project:
            arc = [a for a in arc if a["project"] == project]
        return arc

    def cleanup_for_project_delete(self, project):
        """Unseen/Unanswered Content Guard -- returns
        (cleaned_count, archived_count)."""
        keep, moved = [], []
        for m in self.state["messages"]:
            if m["project"] != project:
                keep.append(m)
                continue
            if m["read"] or m["replied"]:
                continue  # clean -- simply dropped
            moved.append(m)
        self.state["messages"] = keep
        self.state["archived"].extend(moved)
        self._save()
        return moved

    def permanent_clean_archived(self, project=None):
        if project:
            self.state["archived"] = [a for a in self.state["archived"] if a["project"] != project]
        else:
            self.state["archived"] = []
        self._save()
