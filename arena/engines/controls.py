"""Control engines — NOT real OCR. They validate the metrics (oracle must score ~perfect, the
hallucinator must score badly on hallucination) and give the report reference bars."""
import json
import random
import re
from pathlib import Path

from .base import Engine, EngineResult
from ..docgen.content import sentence, DE_NOUNS


def _truth(pdf_path):
    return json.loads(Path(pdf_path).with_suffix(".truth.json").read_text())


def _md(page):
    """Ground truth as markdown: tables become pipe tables, everything else plain lines."""
    out = []
    for r in page["regions"]:
        if r["kind"] == "table":
            rows = r["rows"]
            out.append("| " + " | ".join(rows[0]) + " |")
            out.append("|" + "---|" * len(rows[0]))
            out += ["| " + " | ".join(x) + " |" for x in rows[1:]]
        elif r["text"]:
            out.append(r["text"])
    return "\n".join(out)


class Oracle(Engine):
    name, label, kind = "control_oracle", "Control: oracle (ground truth)", "control"
    notes = "Returns the ground truth. Must score 0% error — validates the scoring."

    def run(self, pdf_path, n_pages):
        return EngineResult(pages=[_md(p) for p in _truth(pdf_path)["pages"]])


class Hallucinator(Engine):
    name, label, kind = "control_hallucinator", "Control: hallucinating VLM (simulated)", "control"
    notes = ("Simulates a fluent VLM failure: correct text, but with fabricated sentences, swapped digits "
             "and text invented for photo-only pages. Must rank worst on hallucination.")

    def run(self, pdf_path, n_pages):
        t = _truth(pdf_path)
        r = random.Random(7)
        out = []
        for pg in t["pages"]:
            txt = _md(pg)
            if pg["blank"]:
                out.append(sentence(r, t["lang"]) + " " + sentence(r, t["lang"]))
                continue
            lines = txt.split("\n")
            res = []
            for ln in lines:
                if r.random() < 0.15:
                    res.append(sentence(r, t["lang"]))  # plausible invented sentence
                digits = [i for i, c in enumerate(ln) if c.isdigit()]
                if digits and r.random() < 0.15:  # swap two adjacent digits -> plausible-looking wrong number
                    i = r.choice(digits)
                    if i + 1 < len(ln) and ln[i + 1].isdigit():
                        ln = ln[:i] + ln[i + 1] + ln[i] + ln[i + 2:]
                res.append(ln)
            out.append("\n".join(res))
        return EngineResult(pages=out)
