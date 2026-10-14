import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import Engine, EngineResult, render_pages


class TesseractCLI(Engine):
    name, label, kind = "tesseract", "Tesseract (raw CLI)", "local"
    notes = "Plain tesseract on 200 dpi page images, lang deu+eng. The classic baseline."

    def available(self):
        if not shutil.which("tesseract"):
            return False, "tesseract not installed (sudo apt install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng)"
        langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout
        if "deu" not in langs:
            return False, "tesseract language 'deu' missing (sudo apt install tesseract-ocr-deu)"
        return True, "ok"

    def run(self, pdf_path, n_pages):
        out = []
        with tempfile.TemporaryDirectory() as td:
            for i, png in enumerate(render_pages(pdf_path, 200)):
                f = Path(td) / f"{i}.png"
                f.write_bytes(png)
                r = subprocess.run(["tesseract", str(f), "stdout", "-l", "deu+eng", "--psm", "3"],
                                   capture_output=True, text=True)
                out.append(r.stdout)
        return EngineResult(pages=out)
