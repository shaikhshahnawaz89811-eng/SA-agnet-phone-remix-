"""
core/helpers.py
Small shared sub-helpers: CI-Workflow Auto-Create, README Sync.

Note: pdf_export_helper and dead_code_check were removed -- both were
superseded orphans (Rule 6). Real PDF export is in core/pdf_and_zip.py
(export_pdf), dead-code risk-check logic is in core/scan_engine.py.
"""
import os
from core import data_store as ds


def ci_workflow_auto_create(project_name, is_apk):
    """(Addendum 21) Only for APK-type projects. Detect existing CI
    config -> reuse instead of overwrite. [v26] record file-name +
    job-identifier so the Remote-Build Monitor never assumes a
    hardcoded name."""
    if not is_apk:
        return None
    pdir = ds.project_dir(project_name)
    wf_dir = os.path.join(pdir, ".github", "workflows")
    os.makedirs(wf_dir, exist_ok=True)
    wf_path = os.path.join(wf_dir, "android-build.yml")
    job_id = "android-build"
    if os.path.exists(wf_path):
        return {"file": wf_path, "job_id": job_id, "reused": True}
    with open(wf_path, "w", encoding="utf-8") as f:
        f.write(
            "name: Android CI\n"
            "on: [push]\n"
            "jobs:\n"
            f"  {job_id}:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: Build with Gradle\n"
            "        run: ./gradlew assembleDebug\n"
        )
    ci_state = ds.load("ci_records", {})
    ci_state[project_name] = {"file": wf_path, "job_id": job_id}
    ds.save("ci_records", ci_state)
    return {"file": wf_path, "job_id": job_id, "reused": False}


def readme_sync(project_name, structural_change_summary=None):
    """Create README on project creation; only update on STRUCTURAL
    changes, never on cosmetic fixes (Addendum 21)."""
    pdir = ds.project_dir(project_name)
    readme_path = os.path.join(pdir, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# {project_name}\n\nSetup steps:\n1. TBD\n\nStructure:\nTBD\n")
        return "created"
    if structural_change_summary:
        with open(readme_path, "a", encoding="utf-8") as f:
            f.write(f"\n## Update ({ds.now_iso()})\n{structural_change_summary}\n")
        return "updated"
    return "unchanged"
