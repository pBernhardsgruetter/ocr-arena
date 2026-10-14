"""Turn saved engine outputs + ground truth into metrics. Pure re-scoring: never re-runs engines."""
import json
from pathlib import Path
from rapidfuzz.distance import Levenshtein

from .metrics import accuracy, hallucination, structure
from .metrics.text import clean, tokens
from . import runner

SUM_KEYS = ["ref_chars", "char_dist", "ref_toks", "tok_dist"]


def score_page(tp: dict, hyp: str) -> dict:
    ref = tp["text"]
    rc, hc = clean(ref), clean(hyp)
    rt, ht = tokens(ref), tokens(hyp)
    h = hallucination.analyze(ref, hyp)
    regions = tp["regions"]
    hand = [accuracy.region_match(r["text"], hyp) for r in regions if r["kind"] == "handwritten"]
    tabs = [structure.table_f1(r["rows"], hyp) for r in regions if r["kind"] == "table"]
    order = structure.reading_order([r["text"] for r in regions if r["kind"] == "printed"], hyp)
    return {"ref_chars": len(rc), "char_dist": Levenshtein.distance(rc, hc) if rc else len(hc),
            "ref_toks": len(rt), "tok_dist": Levenshtein.distance(rt, ht) if rt else len(ht),
            "cer": accuracy.cer(ref, hyp), "halluc": h.__dict__, "hand": hand, "tables": tabs, "order": order,
            "blank": tp["blank"], "hyp_chars": len(hc)}


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def score_doc(truth: dict, rec: dict) -> dict:
    ok = rec.get("status") == "ok"
    hyp_pages = rec.get("pages", []) if ok else []
    pages = []
    for i, tp in enumerate(truth["pages"]):
        hyp = hyp_pages[i] if i < len(hyp_pages) else ""
        pages.append(score_page(tp, hyp))
    agg = {k: sum(p[k] for p in pages) for k in SUM_KEYS}
    H = hallucination.Halluc()
    for p in pages:
        H.add(hallucination.Halluc(**p["halluc"]))
    r = H.rates()
    n = truth["n_pages"]
    usage = rec.get("usage", {}) or {}
    return {
        "status": rec.get("status"), "error": rec.get("error"),
        "cer": (agg["char_dist"] / agg["ref_chars"]) if agg["ref_chars"] else 0.0,
        "wer": (agg["tok_dist"] / agg["ref_toks"]) if agg["ref_toks"] else 0.0,
        **r, "halluc_counts": H.__dict__,
        "handwriting": _mean([x for p in pages for x in p["hand"]]),
        "table_f1": _mean([x for p in pages for x in p["tables"]]),
        "reading_order": _mean([p["order"] for p in pages]),
        "seconds": rec.get("seconds"), "wall_s": rec.get("wall_s"), "sec_per_page": (rec.get("wall_s") or 0) / n,
        "rss_mb": rec.get("rss_mb"), "cost_usd": usage.get("cost_usd"), "usage": usage, "n_pages": n,
        "page_cer": [round(p["cer"], 4) for p in pages],
    }


def score_all(out_dir: Path = runner.OUT, corpus: Path = runner.CORPUS) -> dict:
    truths = {m["id"]: json.loads((corpus / f"{m['id']}.truth.json").read_text()) for m in runner.docs(corpus)}
    res = {}
    for ed in sorted(p for p in out_dir.glob("*") if p.is_dir()):
        for did, truth in truths.items():
            f = ed / f"{did}.json"
            if f.exists():
                res.setdefault(ed.name, {})[did] = score_doc(truth, json.loads(f.read_text()))
    return res
