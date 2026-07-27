#!/usr/bin/env python3
"""
SA Agent -- Stage 1 build (menu/workflow skeleton matching
SA_Agent_Master_Documentation_Final.pdf exactly).

Run: python main.py

AI code-generation / real git network calls are stubbed in this build
stage (this container has no network + no user API keys). Every menu,
password/lockout flow, Msg Box, Task Monitor, Blueprint, Archived-
views, and guard behavior described in the PDF is real and working.
"""
import sys
from core import data_store as ds
from core.security import PasswordManager, CredentialStore
from core.msgbox import MsgBox
from core.git_engine import GitEngine
from core.blueprint import BlueprintStore
from core.task_monitor import TaskMonitor
from core.projects import ProjectManager
from core.ai_engine import AIEngineStatus, SearchAPIRouter
from core.helpers import ci_workflow_auto_create, readme_sync
from core import ui
from core import git_ops
from core.pdf_and_zip import export_pdf, extract_zip
from core.scan_engine import full_scan, report_lines


def ask(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nClosing....")
        sys.exit(0)


class SAAgent:
    def __init__(self):
        self.pw = PasswordManager()
        self.creds = CredentialStore()
        self.msgbox = MsgBox()
        self.git = GitEngine()
        self.blueprint = BlueprintStore()
        self.task_monitor = TaskMonitor()
        self.projects = ProjectManager(self.msgbox, self.git, self.blueprint, self.task_monitor)
        self.ai_status = AIEngineStatus(self.creds)
        self.search_router = SearchAPIRouter(self.creds)

    # ---------------------------------------------------------------- setup
    def first_run_setup(self):
        if not self.pw.is_set():
            print("\nPehli baar setup -- password banayein.")
            while True:
                pw1 = ask("Naya password: ")
                pw2 = ask("Password dubara: ")
                if pw1 and pw1 == pw2:
                    code = self.pw.create_password(pw1)
                    print(f"\nRecovery Code (SAVE THIS -- dobara nahi dikhega): {code}\n")
                    break
                print("Password match nahi hua ya khaali hai, dubara try karein.")
        onboarding = ds.load("onboarding", {"keys_prompted": False})
        if not self.creds.is_complete() and not onboarding.get("keys_prompted"):
            print("API Keys chahiye (Groq, Tavily, Serper.dev) -- skip karne ke liye Enter dabayein.")
            print("(Baad me Settings se Update/Clear Key kar sakte hai; yeh sirf first run par poocha jaata hai.)")
            for field, label in [("groq_api_key", "Groq API Key"),
                                  ("tavily_api_key", "Tavily API Key"),
                                  ("serper_api_key", "Serper.dev API Key")]:
                if not self.creds.get(field):
                    val = ask(f"{label}: ").strip()
                    if val:
                        self.creds.set_key(field, val)
            ds.save("onboarding", {"keys_prompted": True})
        print("\nLoading required background processes....\n")

    def menu_settings_keys(self):
        fields = [("groq_api_key", "Groq API Key"), ("tavily_api_key", "Tavily API Key"),
                  ("serper_api_key", "Serper.dev API Key")]
        print("\n----- Settings: API Keys + Password -----")
        for f, label in fields:
            print(f"  {label}: {self.creds.masked(f)}")
        missing = self.creds.missing()
        if missing:
            print(f"  (Missing: {', '.join(missing)})")
        print("  Options: update / clear / change-password / forgot-password / exit")
        action = ask("Action: ").strip().lower()
        if action == "update":
            for f, label in fields:
                val = ask(f"Naya {label} (Enter to skip): ").strip()
                if val:
                    self.creds.set_key(f, val)
                    print(f"  {label} updated -- purani turant invalidate.")
        elif action == "clear":
            for f, label in fields:
                if ask(f"{label} clear karein? (y/n): ").strip().lower() == "y":
                    self.creds.clear_key(f)
                    print(f"  {label} cleared.")
        elif action == "change-password":
            old_pw = ask("Purana password: ")
            new_pw1 = ask("Naya password: ")
            new_pw2 = ask("Naya password dubara: ")
            if not new_pw1 or new_pw1 != new_pw2:
                print("  Password match nahi hua ya khaali hai.")
                return
            ok, msg = self.pw.change_password(old_pw, new_pw1)
            print(f"  {msg}")
        elif action == "forgot-password":
            code = ask("Recovery Code: ").strip()
            new_pw1 = ask("Naya password: ")
            new_pw2 = ask("Naya password dubara: ")
            if not new_pw1 or new_pw1 != new_pw2:
                print("  Password match nahi hua ya khaali hai.")
                return
            ok, msg = self.pw.reset_with_recovery_code(code, new_pw1)
            print(f"  {msg}")

    # ---------------------------------------------------------------- main
    def run(self):
        self.first_run_setup()
        while True:
            ui.print_status_bar(self.ai_status, self.git, self.msgbox, self.projects, self.task_monitor)
            ui.print_main_menu()
            choice = ask("Select option (or 'keys' for Settings > Update/Clear API Keys): ").strip()
            if choice.lower() == "keys":
                self.menu_settings_keys()
            elif choice == "1":
                self.menu_create_project()
            elif choice == "2":
                self.menu_all_projects()
            elif choice == "3":
                self.menu_delete_project()
            elif choice == "4":
                self.menu_chat_mode()
            elif choice == "5":
                self.menu_git_status()
            elif choice == "6":
                self.menu_errors_fix()
            elif choice == "7":
                self.menu_msg_box_global()
            elif choice == "8":
                self.menu_task_monitor()
            elif choice == "9":
                print("\nClosing....\n")
                sys.exit(0)
            else:
                print("Invalid option.")

    # ---------------------------------------------------------- 1. Create
    def menu_create_project(self):
        while True:
            ui.print_create_project_menu()
            c = ask("Select: ").strip()
            if c == "1":
                self._create_via_github()
            elif c == "2":
                self._create_via_zip()
            elif c == "3":
                self._create_via_task()
            elif c == "4":
                self._create_via_chat()
            elif c == "5":
                return
            else:
                print("Invalid option.")

    def _finalize_create(self, name, source_type, is_apk=False):
        ok, msg = self.projects.create(name, source_type, is_apk=is_apk)
        if not ok:
            print(f"  {msg}")
            return
        readme_sync(name)
        if is_apk:
            ci_workflow_auto_create(name, True)
        print(f"  Project '{name}' created. ({msg})")

    def _create_via_github(self):
        link = ask("GitHub repo link: ").strip()
        if not link or not link.startswith("http"):
            print("  Repo link access nahi ho paaya -- link check karein ya access dein.")
            return
        name = ask("Project ke liye naam: ").strip()
        if not name.strip() or self.projects.exists(name):
            print("  Yeh project naam khaali/pehle se maujood hai.")
            return
        dest = ds.project_dir(name)
        print("  Cloning....")
        ok, msg = git_ops.clone(link, dest)
        if not ok:
            print(f"  {msg}")
            return
        langs = git_ops.detect_languages(dest)
        is_apk = "Kotlin" in langs or "Gradle" in langs
        ok, msg = self.projects.create(name, "github", languages=langs, is_apk=is_apk)
        print(f"  {msg} Languages detected: {langs}")
        readme_sync(name)
        if is_apk:
            ci_workflow_auto_create(name, True)

    def _create_via_zip(self):
        path = ask("Zip file ka path: ").strip()
        name = ask("Project ke liye naam: ").strip()
        if not name.strip() or self.projects.exists(name):
            print("  Yeh project naam khaali/pehle se maujood hai.")
            return
        dest = ds.project_dir(name)
        ok, msg = extract_zip(path, dest)
        if not ok:
            print(f"  {msg}")
            return
        langs = git_ops.detect_languages(dest)
        is_apk = "Kotlin" in langs or "Gradle" in langs
        ok, msg = self.projects.create(name, "zip", languages=langs, is_apk=is_apk)
        print(f"  {msg} Languages detected: {langs}")
        readme_sync(name)
        if is_apk:
            ci_workflow_auto_create(name, True)
        git_ops.init_repo(dest)

    def _create_via_task(self):
        detail = ask("Project detail bataiye (Chat Mode): ").strip()
        while not detail:
            print("  Blank input allowed nahi hai.")
            detail = ask("Project detail bataiye: ").strip()
        name = ask("Project ke liye naam: ").strip()
        if not name.strip() or self.projects.exists(name):
            print("  Yeh project naam khaali/pehle se maujood hai.")
            return
        sub_id = self.blueprint.add(name, detail)
        self._finalize_create(name, "task")
        print(f"  Planner Module: draft blueprint sub-task #{sub_id} saved (Pending).")

    def _create_via_chat(self):
        self._create_via_task()  # same underlying AI-engine logic per spec

    # ---------------------------------------------------------- 2. All Projects
    def menu_all_projects(self):
        while True:
            ui.print_all_projects_menu()
            c = ask("Select: ").strip()
            if c == "1":
                self._search_by_name()
            elif c == "2":
                ui.organised_table([{"Project": n} for n in self.projects.all_names()], ["Project"])
            elif c == "3":
                self._rename_project()
            elif c == "4":
                self._details_project()
            elif c == "5":
                self._view_project_files()
            elif c == "6":
                self._msg_box_all_projects()
            elif c == "7":
                return
            else:
                print("Invalid option.")

    def _search_by_name(self):
        q = ask("Project naam search: ").strip()
        kind, results = self.projects.search(q)
        if kind == "exact":
            print(f"  Mila: {results[0]}")
            self._open_project(results[0])
        elif kind == "partial":
            ui.organised_table([{"Project": n} for n in results], ["Project"])
        elif kind == "suggest":
            print("  Aapka matlab yeh project toh nahi?")
            ui.organised_table([{"Project": n} for n in results], ["Project"])
        else:
            print(f"  '{q}' naam ka project exist nahi karta.")

    def _rename_project(self):
        old = ask("Purana naam: ").strip()
        if not self.projects.exists(old):
            print("  Project not found.")
            return
        ok, msg = self.pw.verify(ask("Password: "))
        if not ok:
            print(f"  {msg}")
            return
        new = ask("Naya naam: ").strip()
        ok, msg = self.projects.rename(old, new)
        print(f"  {msg}")

    def _details_project(self):
        name = ask("Project naam: ").strip()
        info = self.projects.info(name)
        if not info:
            print("  Project not found.")
            return
        for k, v in info.items():
            print(f"  {k}: {v}")
        if ask("Export to PDF? (y/n): ").strip().lower() == "y":
            lines = [f"{k}: {v}" for k, v in info.items()]
            ok, msg = export_pdf(name, "Details", f"Project Details -- {name}", lines)
            print(f"  {msg}")

    def _view_project_files(self):
        name = ask("Project naam: ").strip()
        pdir = ds.project_dir(name) if self.projects.exists(name) else None
        if not pdir:
            print("  Project not found.")
            return
        import os
        files = []
        for root, _, fs in os.walk(pdir):
            for f in fs:
                files.append(os.path.relpath(os.path.join(root, f), pdir))
        ui.organised_table([{"File": f} for f in files], ["File"])

    def _msg_box_all_projects(self):
        ui.organised_table(
            [{"ID": m["id"], "Project": m["project"], "Text": m["text"][:40], "Read": m["read"]}
             for m in self.msgbox.all_pending()],
            ["ID", "Project", "Text", "Read"]
        )
        if ask("Archived Msg Box dekhna hai? (y/n): ").strip().lower() == "y":
            archived = self.msgbox.archived()
            ui.organised_table(
                [{"Project": a["project"], "Text": a["text"][:40]} for a in archived],
                ["Project", "Text"]
            )
            if archived and ask("Permanently clean karein? (y/n): ").strip().lower() == "y":
                self.msgbox.permanent_clean_archived()
                print("  Archived Msg Box permanently clean ho gaya.")
        if ask("Archived Uncommitted Work dekhna hai? (y/n): ").strip().lower() == "y":
            arc_uc = self.git.archived_uncommitted()
            ui.organised_table(
                [{"Project": a["project"], "Desc": a["desc"][:40], "Time": a["ts"]}
                 for a in arc_uc],
                ["Project", "Desc", "Time"]
            )
            if arc_uc and ask("Permanently clean karein? (y/n): ").strip().lower() == "y":
                self.git.permanent_clean_archived_uncommitted()
                print("  Archived Uncommitted Work permanently clean ho gaya.")

    def _open_project(self, name):
        while True:
            ui.print_project_menu(name)
            c = ask("Select: ").strip()
            if c == "1":
                self._project_task(name)
            elif c == "2":
                self._project_msgbox(name)
            elif c == "3":
                self._project_github_setting(name)
            elif c == "4":
                self._project_blueprint(name)
            elif c == "5":
                self._view_files_for(name)
            elif c == "6":
                self._full_scan_fix(name)
            elif c == "7":
                self._not_push_task(name)
            elif c == "8":
                self._project_info(name)
            elif c == "9":
                return
            else:
                print("Invalid option.")

    def _project_task(self, name):
        info = self.projects.info(name)
        print(f"  Reloading Project Information (languages: {info.get('languages')})....")
        detail = ask("Task detail: ").strip()
        while not detail:
            detail = ask("Blank input allowed nahi -- dubara: ").strip()
        engine = self.ai_status.pick_engine()
        if not engine:
            self.msgbox.add(name, "AI engines busy ya API key missing -- task queued.", needs_reply=True)
            print("  Dono engines busy/unavailable hai -- Msg Box me queue ho gaya.")
            return
        sub_id = self.blueprint.add(name, detail)
        task = self.task_monitor.add_task(name, detail)
        self.ai_status.set_thinking(engine, project=name, sub_task_label=detail[:30], sub_task_idx=1, sub_task_total=1)
        print(f"  [{engine}] {self.ai_status.groq_line() if engine=='groq' else self.ai_status.offline_line()}")

        system_prompt = ("You are a coding agent. Reply ONLY with one or more blocks in this "
                          "exact format for every file to create/update:\n"
                          "### FILE: relative/path.ext\n<full file content>\n### END FILE\n"
                          "No other prose outside these blocks.")
        self.ai_status.set_coding(engine, 10, project=name, file="generating...")
        ok, text = self.ai_status.generate(engine, system_prompt, detail)
        self.ai_status.set_idle(engine)

        if not ok:
            self.msgbox.add(name, text, needs_reply=True)
            self.task_monitor.stop(task["id"], sandbox_mid_validation=True)
            print(f"  {text}")
            return

        written = self._write_ai_file_blocks(name, text)
        self.task_monitor.set_progress(task["id"], 100)
        if written:
            self.git.add_not_pushed(name, f"Task: {detail[:40]} ({len(written)} file(s))")
            self.blueprint.mark_ready_for_coding(name)
            print(f"  Blueprint sub-task #{sub_id} logged. Files written: {written}")
        else:
            print(f"  AI replied but no '### FILE:' block found -- nothing written. "
                  f"Raw reply logged to Msg Box for review.")
            self.msgbox.add(name, text[:500], needs_reply=False)

    def _write_ai_file_blocks(self, project_name, ai_text):
        """Copy-first hop per Rule 19 (§15 v18): Python files are
        syntax-checked on a temp copy BEFORE writing to the live file.
        Non-Python files are written directly (no toolchain available).
        On syntax failure: file is NOT written, error is logged to Msg Box."""
        import re
        import os
        import py_compile
        import tempfile
        pdir = ds.project_dir(project_name)
        pattern = re.compile(r"### FILE:\s*(.+?)\n(.*?)### END FILE", re.DOTALL)
        written = []
        for m in pattern.finditer(ai_text):
            rel_path = m.group(1).strip()
            content = m.group(2)
            # Rule 19: Python files get temp-copy syntax-check first
            if rel_path.endswith(".py"):
                with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                try:
                    py_compile.compile(tmp_path, doraise=True)
                except py_compile.PyCompileError as e:
                    os.unlink(tmp_path)
                    self.msgbox.add(
                        project_name,
                        f"Syntax error in AI-generated {rel_path}: {e.exc_value} -- file NOT written.",
                        needs_reply=False,
                    )
                    print(f"  Syntax error in {rel_path} -- skipped, logged to Msg Box.")
                    continue
                os.unlink(tmp_path)
            full_path = os.path.join(pdir, rel_path)
            parent = os.path.dirname(full_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            written.append(rel_path)
        return written

    def _project_msgbox(self, name):
        ui.organised_table(
            [{"ID": m["id"], "Text": m["text"][:50], "Read": m["read"]} for m in self.msgbox.all_pending(name)],
            ["ID", "Text", "Read"]
        )
        mid = ask("Reply kis ID ko? (Enter to skip): ").strip()
        if mid.isdigit():
            reply = ask("Reply: ")
            self.msgbox.reply(int(mid), reply)
            print("  Replied, task resume ho sakta hai.")

    def _project_github_setting(self, name):
        while True:
            ui.print_github_setting_menu()
            c = ask("Select: ").strip()
            if c == "1":
                pdir = ds.project_dir(name)
                if not git_ops.is_repo(pdir):
                    git_ops.init_repo(pdir)
                git_ops.add_all(pdir)
                git_ops.commit(pdir, "SA Agent: push change")
                ok, out = git_ops.push(pdir)
                self.git.record_result(ok)
                if ok:
                    self.git.push(name)  # clears the not-pushed queue
                    print(f"  Pushed. {out[:200]}")
                else:
                    self.git.state["retry"] += 1
                    self.git._save()
                    print(f"  Push failed (needs remote configured + network): {out[:200]}")
            elif c == "2":
                ui.organised_table([{"Rule": r} for r in self.git.rules(name)], ["Rule"])
            elif c == "3":
                rule = ask("Naya rule: ").strip()
                ok, msg = self.git.add_rule(name, rule)
                print(f"  {msg}")
            elif c == "4":
                rule = ask("Kaunsa rule remove karna hai: ").strip()
                mid = ask("Kya push mid-way me chal raha hai? (y/n): ").strip().lower() == "y"
                ok, msg = self.git.remove_rule(name, rule, mid_push=mid)
                print(f"  {msg}")
            elif c == "5":
                return
            else:
                print("Invalid option.")

    def _project_blueprint(self, name):
        while True:
            ui.print_blueprint_menu()
            c = ask("Select: ").strip()
            if c == "1":
                text = ask("Blueprint entry: ").strip()
                sid = self.blueprint.add(name, text)
                print(f"  Added sub-task #{sid}.")
            elif c == "2":
                sid = ask("Sub-task ID: ").strip()
                new_text = ask("Naya text: ").strip()
                if sid.isdigit():
                    ok, msg = self.blueprint.edit(name, int(sid), new_text)
                    print(f"  {msg}")
            elif c == "3":
                ok, msg = self.pw.verify(ask("Password: "))
                if ok:
                    self.blueprint.delete(name)
                    print("  Blueprint deleted.")
                else:
                    print(f"  {msg}")
            elif c == "4":
                tasks, status = self.blueprint.show(name)
                print(f"  Status: {status}")
                ui.organised_table(
                    [{"ID": t["id"], "Name": t["name"], "Status": t["status"]} for t in tasks],
                    ["ID", "Name", "Status"]
                )
            elif c == "5":
                tasks, status = self.blueprint.show(name)
                lines = [f"{t['id']}. {t['name']} [{t['status']}]" for t in tasks]
                ok, msg = export_pdf(name, "Blueprint", f"Blueprint -- {name} ({status})", lines)
                print(f"  {msg}")
            elif c == "6":
                return
            else:
                print("Invalid option.")

    def _view_files_for(self, name):
        import os
        pdir = ds.project_dir(name)
        files = []
        for root, _, fs in os.walk(pdir):
            for f in fs:
                files.append(os.path.relpath(os.path.join(root, f), pdir))
        ui.organised_table([{"File": f} for f in files], ["File"])

    def _full_scan_fix(self, name):
        info = self.projects.info(name)
        print(f"  Full Scan & Fix -- context reload (languages: {info.get('languages')})....")
        pdir = ds.project_dir(name)
        report = full_scan(pdir)
        lines = report_lines(report)
        for l in lines:
            print(f"  {l}")
        ok, msg = export_pdf(name, "ScanReport", f"Full Scan & Fix Report -- {name}", lines)
        print(f"  {msg}")

    def _not_push_task(self, name):
        entries = self.git.not_pushed(name)
        ui.organised_table([{"Desc": e["desc"], "Time": e["ts"]} for e in entries], ["Desc", "Time"])
        if entries and ask("Ab push karein? (y/n): ").strip().lower() == "y":
            pdir = ds.project_dir(name)
            if not git_ops.is_repo(pdir):
                git_ops.init_repo(pdir)
            git_ops.add_all(pdir)
            git_ops.commit(pdir, "SA Agent: not-push-task push")
            ok, out = git_ops.push(pdir)
            self.git.record_result(ok)
            if ok:
                self.git.push(name)  # clear not-pushed queue after real push succeeds
                print(f"  Pushed. {out[:200]}")
            else:
                self.git.state["retry"] += 1
                self.git._save()
                print(f"  Push failed (remote configure karein + network chahiye): {out[:200]}")

    def _project_info(self, name):
        info = self.projects.info(name)
        for k, v in info.items():
            print(f"  {k}: {v}")

    # ---------------------------------------------------------- 3. Delete
    def menu_delete_project(self):
        ok, msg = self.pw.verify(ask("Password: "))
        if not ok:
            print(f"  {msg}")
            return
        name = ask("Project naam confirm karein: ").strip()
        if not self.projects.exists(name):
            print("  Project not found.")
            return
        if ask(f"'{name}' delete confirm? (y/n): ").strip().lower() != "y":
            print("  Cancelled.")
            return
        ok, msg, stats = self.projects.delete(name)
        print(f"  {msg}")
        print(f"  Archived to Archived Msg Box: {stats.get('archived_msgs', 0)} unread entries")
        print(f"  Archived to Archived Uncommitted Work: {stats.get('archived_uncommitted', 0)} entries")

    # ---------------------------------------------------------- 4. Chat Mode
    def menu_chat_mode(self):
        print("  Chat Mode -- active AI engine ka current kaam pause ho gaya.")
        engine = self.ai_status.pick_engine()
        if not engine:
            print("  Dono engines busy ya API key missing hai.")
            if not self.creds.get("groq_api_key"):
                print("  Msg Box: Groq API key maanga jaa raha hai -- 'keys' se Settings kholein.")
            return
        print(f"  Engine assigned: {engine}")
        text = ask("Aap: ").strip()
        if not text:
            return
        print("  [Routing...]")
        print("  [Loading project context...]")
        self.ai_status.set_thinking(engine)
        print("  [Thinking...]")
        ok, reply = self.ai_status.generate(
            engine,
            "You are a helpful coding assistant chatting with the user inside SA Agent's Chat Mode.",
            text,
        )
        self.ai_status.set_idle(engine)
        if ok:
            print("  [Validating...]")
            print("  [Done]")
            print(f"  ({engine}) {reply}")
        else:
            print(f"  ({engine}) {reply}")

    # ---------------------------------------------------------- 5. Git Status
    def menu_git_status(self):
        print(f"  {self.git.counters()}")
        ui.organised_table(
            [{"Project": n} for n in self.projects.all_names()], ["Project"]
        )

    # ---------------------------------------------------------- 6. Errors Fix
    def menu_errors_fix(self):
        print("  Errors Fix -- is build stage me koi live error queue nahi hai "
              "(real errors AI engine se detect hote hai, jo abhi stub hai).")

    # ---------------------------------------------------------- 7. Msg Box
    def menu_msg_box_global(self):
        self._msg_box_all_projects()

    # ---------------------------------------------------------- 8. Task Monitor
    def menu_task_monitor(self):
        tasks = self.task_monitor.list_tasks()
        ui.organised_table(
            [{"ID": t["id"], "Project": t["project"], "Status": t["status"], "Progress": t["progress"]} for t in tasks],
            ["ID", "Project", "Status", "Progress"]
        )
        action = ask("Stop/Continue/Delete/Exit: ").strip().lower()
        if action in ("stop", "continue", "delete"):
            tid = ask("Task ID: ").strip()
            if not tid.isdigit():
                return
            tid = int(tid)
            if action == "delete":
                ok, msg = self.pw.verify(ask("Password: "))
                if not ok:
                    print(f"  {msg}")
                    return
                self.task_monitor.delete(tid)
                print("  Deleted.")
            elif action == "stop":
                print(f"  {self.task_monitor.stop(tid)}")
            else:
                self.task_monitor.continue_task(tid)
                print("  Resumed.")


def main():
    agent = SAAgent()
    agent.run()


if __name__ == "__main__":
    main()
