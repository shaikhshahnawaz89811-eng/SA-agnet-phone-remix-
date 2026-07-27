"""
core/scan_engine.py
REAL Full Project Scan & Fix Engine (§23) for Python files -- other
languages need their own compiler/linter wired in the same pattern
(this container only ships a Python toolchain).

Per-file: py_compile syntax-check (pass/fail) + AST-based dead-code
candidate detection (unused imports, never-called top-level
functions). Dead-Code Handling (§30, Rule 5-7-14): purpose+risk check
-- since a static scan alone cannot prove a function isn't part of an
advertised public API, this engine NEVER auto-deletes; every candidate
is FLAGGED for human review, never silently removed. That is the safe
reading of "100% safe only" for a tool with no semantic project
context.
"""
import ast
import os
import py_compile
import tempfile


def _syntax_check(path):
    try:
        py_compile.compile(path, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e.exc_value)


def _find_dead_code_candidates(path, project_all_py_files):
    """Unused imports (never referenced in the same file) + top-level
    functions never called anywhere else in the project (best-effort
    text search -- not a full call-graph)."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []

    candidates = []

    # unused imports
    imported_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.append((alias.asname or alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    imported_names.append((alias.asname or alias.name, node.lineno))
    for name, lineno in imported_names:
        # crude but safe: count usages of the bare name elsewhere in file
        if src.count(name) <= 1:
            candidates.append({"type": "unused_import", "name": name, "line": lineno})

    # top-level functions never referenced in the whole project
    top_funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("__")]
    for fname in top_funcs:
        referenced_elsewhere = False
        for other_path in project_all_py_files:
            if other_path == path:
                continue
            try:
                with open(other_path, "r", encoding="utf-8", errors="ignore") as f:
                    if fname in f.read():
                        referenced_elsewhere = True
                        break
            except OSError:
                continue
        if not referenced_elsewhere and src.count(fname) <= 1:
            candidates.append({"type": "unused_function", "name": fname, "line": None})

    return candidates


def full_scan(project_dir):
    """Returns an organised report dict, per Rule 13 cleaner-viewer
    (§34): per-file grouped, not a raw dump."""
    py_files = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "Exports")]
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))

    report = {"fixed": [], "dead_code_flagged": [], "error_pending": [], "clean": []}

    for path in py_files:
        rel = os.path.relpath(path, project_dir)
        ok, err = _syntax_check(path)
        if not ok:
            report["error_pending"].append({"file": rel, "error": err})
            continue
        candidates = _find_dead_code_candidates(path, py_files)
        if candidates:
            report["dead_code_flagged"].append({"file": rel, "candidates": candidates})
        else:
            report["clean"].append({"file": rel})

    return report


def report_lines(report):
    lines = []
    lines.append(f"Clean files: {len(report['clean'])}")
    if report["fixed"]:
        lines.append(f"Fixed files: {len(report['fixed'])}")
        for f in report["fixed"]:
            lines.append(f"  - {f['file']}: {f.get('note', 'fixed')}")
    lines.append(f"Dead-code flagged (review-needed): {len(report['dead_code_flagged'])}")
    for d in report["dead_code_flagged"]:
        names = ", ".join(f"{c['type']}:{c['name']}" for c in d["candidates"])
        lines.append(f"  - {d['file']}: {names}")
    lines.append(f"Error still pending: {len(report['error_pending'])}")
    for e in report["error_pending"]:
        lines.append(f"  - {e['file']}: {e['error'][:80]}")
    return lines
