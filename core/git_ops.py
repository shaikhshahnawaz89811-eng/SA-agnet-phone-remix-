"""
core/git_ops.py
REAL git operations via subprocess (not simulated) -- clone, init,
add/commit, push, and status/retry-reconcile parsing (§6, §17, §28).

These call the actual `git` binary. Clone/push need network on your
device; local operations (init/add/commit/status) work offline. Every
method returns (ok: bool, message: str) so callers can route failures
into the exact Msg Box text the spec requires, never a silent crash.
"""
import subprocess
import os


def _run(args, cwd=None, timeout=120):
    try:
        result = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return False, "git binary not found on this system."
    except subprocess.TimeoutExpired:
        return False, "git operation timed out (network issue?)." 


def clone(repo_url, dest_dir):
    """(§6) Invalid/private/unreachable link -> spec's exact message."""
    ok, out = _run(["git", "clone", repo_url, dest_dir], timeout=180)
    if not ok:
        return False, "Repo link access nahi ho paaya -- link check karein ya access dein."
    return True, out


def init_repo(project_dir):
    return _run(["git", "init"], cwd=project_dir)


def add_all(project_dir):
    return _run(["git", "add", "-A"], cwd=project_dir)


def commit(project_dir, message):
    ok, out = _run(["git", "commit", "-m", message], cwd=project_dir)
    if not ok and "nothing to commit" in out.lower():
        return True, "Nothing to commit."
    return ok, out


def set_remote(project_dir, remote_url):
    ok, out = _run(["git", "remote", "remove", "origin"], cwd=project_dir)
    if not ok:
        return False, out
    return _run(["git", "remote", "add", "origin", remote_url], cwd=project_dir)


def push(project_dir, branch="main"):
    """[v17] Reconcile check before push: detect partial/half-committed
    state (uncommitted changes) and commit them first so a push never
    goes out half-done."""
    dirty_ok, dirty_out = _run(["git", "status", "--porcelain"], cwd=project_dir)
    if dirty_ok and dirty_out.strip():
        add_all(project_dir)
        commit(project_dir, "SA Agent: auto-commit before push (reconcile)")
    ok, out = _run(["git", "push", "-u", "origin", branch], cwd=project_dir)
    return ok, out


def status(project_dir):
    return _run(["git", "status", "--porcelain"], cwd=project_dir)


def is_repo(project_dir):
    return os.path.isdir(os.path.join(project_dir, ".git"))


def detect_languages(project_dir):
    """[v18] Per-component language/tech list, not a single field."""
    ext_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".java": "Java", ".kt": "Kotlin", ".xml": "XML/Gradle-resource",
        ".gradle": "Gradle", ".dart": "Dart", ".go": "Go", ".rs": "Rust",
        ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C",
        ".swift": "Swift", ".html": "HTML", ".css": "CSS",
    }
    found = set()
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ext_map:
                found.add(ext_map[ext])
    return sorted(found)

