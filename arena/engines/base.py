from dataclasses import dataclass, field


@dataclass
class EngineResult:
    pages: list[str]                      # one text/markdown string per page (index = page-1)
    usage: dict = field(default_factory=dict)  # e.g. {"in_tokens":..,"out_tokens":..,"cost_usd":..}
    meta: dict = field(default_factory=dict)


class Engine:
    name = "base"
    label = "Base"
    kind = "local"           # local | api | control
    notes = ""

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or {}

    def available(self) -> tuple[bool, str]:
        return True, "ok"

    def run(self, pdf_path: str, n_pages: int) -> EngineResult:
        raise NotImplementedError

    def describe(self) -> dict:
        ok, why = self.available()
        return {"name": self.name, "label": self.label, "kind": self.kind, "available": ok,
                "reason": why, "notes": self.notes}


def render_pages(pdf_path: str, dpi: int = 150) -> list[bytes]:
    import pymupdf
    out = []
    with pymupdf.open(pdf_path) as d:
        for pg in d:
            out.append(pg.get_pixmap(dpi=dpi).tobytes("png"))
    return out
