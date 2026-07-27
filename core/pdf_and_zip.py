"""
core/pdf_and_zip.py
REAL PDF-Export Helper (reportlab, Addendum 11) and REAL zip
extraction (§7) -- corrupt/password-protected zips get the exact
spec error message instead of a traceback.
"""
import os
import zipfile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from core import data_store as ds


def export_pdf(project_name, section_name, title, lines):
    """Organised/sectioned PDF (Rule 13 cleaner-viewer), duplicate-name
    check via timestamp suffix, saved to the project's Exports/ folder.
    Never claims silent success on failure -- returns (ok, message)."""
    exports_dir = os.path.join(ds.project_dir(project_name), "Exports")
    os.makedirs(exports_dir, exist_ok=True)
    base = section_name.replace(" ", "_")
    fname = f"{base}_{ds.now_iso().replace(':', '-')}.pdf"
    path = os.path.join(exports_dir, fname)
    try:
        c = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        y = height - 20 * mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(20 * mm, y, title)
        y -= 10 * mm
        c.setFont("Helvetica", 10)
        for line in lines:
            if y < 20 * mm:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 20 * mm
            c.drawString(20 * mm, y, str(line)[:110])
            y -= 6 * mm
        c.save()
        return True, f"PDF saved: {path}"
    except Exception as e:
        return False, f"Pending -- manual export needed ({e})."


def extract_zip(zip_path, dest_dir):
    """(§7) Corrupt/password-protected -> spec's exact error message."""
    if not os.path.isfile(zip_path):
        return False, "Zip file corrupt hai ya password-protected hai -- dusri file try karein."
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            if bad is not None:
                return False, "Zip file corrupt hai ya password-protected hai -- dusri file try karein."
            zf.extractall(dest_dir)
        return True, dest_dir
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
        # RuntimeError covers "password required"; NotImplementedError
        # covers unsupported-compression edge cases -- both map to the
        # same user-facing message per spec.
        return False, "Zip file corrupt hai ya password-protected hai -- dusri file try karein."
