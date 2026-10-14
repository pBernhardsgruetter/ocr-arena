import socket
from urllib.parse import urlparse

from .base import Engine, EngineResult


class LiteParseEngine(Engine):
    """LiteParse (PDFium + OCR). mode: markdown | text. OCR backend: bundled Tesseract,
    or an HTTP OCR server (EasyOCR / PaddleOCR, see liteparse/ocr/)."""
    kind = "local"

    def __init__(self, name, label, mode="markdown", ocr=True, server_url=None, lang="deu", notes="", cfg=None):
        super().__init__(cfg)
        self.name, self.label, self.mode, self.ocr, self.server_url, self.lang = name, label, mode, ocr, server_url, lang
        self.notes = notes

    def available(self):
        try:
            import liteparse  # noqa: F401
        except ImportError:
            return False, "pip package 'liteparse' not installed"
        if self.server_url:
            u = urlparse(self.server_url)
            try:
                socket.create_connection((u.hostname, u.port or 80), timeout=2).close()
            except OSError:
                return False, f"OCR server not reachable at {self.server_url} (see liteparse/ocr/ README)"
        return True, "ok"

    def run(self, pdf_path, n_pages):
        from liteparse import LiteParse
        kw = dict(ocr_enabled=self.ocr, output_format=self.mode, dpi=self.cfg.get("dpi", 150), quiet=True,
                  num_workers=self.cfg.get("workers", 4), max_pages=max(n_pages, 1))
        if self.ocr:
            kw["ocr_language"] = self.lang
            if self.server_url:
                kw["ocr_server_url"] = self.server_url
        res = LiteParse(**kw).parse(pdf_path)
        pages = [(p.markdown if self.mode == "markdown" else p.text) or "" for p in res.pages]
        pages += [""] * (n_pages - len(pages))
        return EngineResult(pages=pages)
