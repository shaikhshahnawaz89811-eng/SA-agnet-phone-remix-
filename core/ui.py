"""
core/ui.py
Menu bar + status bar + tracking-counter rendering (§1-§3, §34
Cleaner-Viewer organised-display).
"""


def clear():
    print("\n" * 2)


def print_status_bar(ai_status, git_engine, msgbox, projects, task_monitor):
    total_pending = len(msgbox.all_pending())
    project_names = len(projects.all_names())
    tasks = len(task_monitor.list_tasks())
    print("-" * 60)
    print(f" Messenger Box: {total_pending} pending   "
          f"Total Pending Works: {total_pending}   "
          f"Project Names: {project_names}   Tasks: {tasks}")
    print(f" {ai_status.groq_line()}")
    print(f" {ai_status.offline_line()}")
    print(f" {git_engine.counters()}")
    print(f" Msg Box: Project [{project_names}] Task [{tasks}] Progress 0%")
    print("-" * 60)


def print_main_menu():
    print("""
==================== MAIN MENU ====================
1. CREATE PROJECT
2. ALL PROJECT
3. DELETE PROJECT
4. CHAT MODE
5. GIT STATUS
6. ERRORS FIX
7. MSG BOX
8. TASK MONITOR
9. EXIT
====================================================""")


def print_create_project_menu():
    print("""
------------- Create Project -------------
1. GitHub Copy
2. Zip
3. Task to Project
4. Chat Mode (Quick Project via Chat)
5. Exit
-------------------------------------------""")


def print_all_projects_menu():
    print("""
------------- All Projects -------------
1. Search by name
2. Show all projects
3. Re-name project
4. Details project
5. View Project Files
6. Msg box
7. Exit
------------------------------------------""")


def print_project_menu(name):
    print(f"""
------------- Project [{name}] -------------
1. Task
2. Msg box
3. GitHub Setting
4. Blueprint
5. View Files
6. Full Scan & Fix
7. Not Push Task
8. Project Information
9. Exit
------------------------------------------""")


def print_github_setting_menu():
    print("""
------- GitHub Setting -------
1. Git push change
2. Show Rules List
3. Rules add
4. Remove Rule
5. Exit
-------------------------------""")


def print_blueprint_menu():
    print("""
------- Blueprint -------
1. Add blueprint
2. Edit Blueprint
3. Delete blueprint (password required)
4. Show blueprint
5. Export to PDF
6. Exit
--------------------------""")


def organised_table(rows, headers):
    """Rule 13 / §34 Cleaner-Viewer: per-item-grouped, not raw dump."""
    if not rows:
        print("  (koi entry nahi hai)")
        return
    widths = [max(len(str(h)), max((len(str(r.get(h, ""))) for r in rows), default=0)) for h in headers]
    print("  " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("  " + "-+-".join("-" * w for w in widths))
    for r in rows:
        print("  " + " | ".join(str(r.get(h, "")).ljust(w) for h, w in zip(headers, widths)))
