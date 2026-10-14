"""Score everything and render a single self-contained HTML report (no network needed)."""
import base64
import json
from pathlib import Path

import pymupdf
from rapidfuzz.distance import Levenshtein

from .. import config, runner, score
from ..engines.registry import build
from ..metrics.text import tokens

HERE = Path(__file__).parent
REPORT = runner.ROOT / "results" / "report"


def _diff(ref: str, hyp: str, limit=700) -> list:
    r, h = tokens(ref), tokens(hyp)
    seg = []
    for tag, i1, i2, j1, j2 in Levenshtein.opcodes(r, h):
        seg.append([tag[0], " ".join(r[i1:i2]), " ".join(h[j1:j2])])  # e/d/i/r
    out, n = [], 0
    for s in seg:  # keep the payload bounded
        n += len(s[1]) + len(s[2])
        if n > limit * 6:
            break
        out.append(s)
    return out


def _thumb(pdf: str, page: int) -> str:
    with pymupdf.open(pdf) as d:
        pix = d[page].get_pixmap(dpi=55)
        return "data:image/jpeg;base64," + base64.b64encode(pix.tobytes("jpeg", jpg_quality=60)).decode()


def _aggregate(per_doc: dict, docs: dict) -> dict:
    """per_doc: {doc_id: score}. Macro-average over profiles."""
    by_prof = {}
    for did, s in per_doc.items():
        by_prof.setdefault(docs[did]["profile"], []).append(s)
    keys = ["cer", "wer", "halluc_rate", "omission_rate", "numeric_error_rate", "handwriting", "table_f1", "reading_order"]
    prof = {}
    for p, xs in by_prof.items():
        prof[p] = {k: (lambda v: sum(v) / len(v) if v else None)([x[k] for x in xs if x[k] is not None]) for k in keys}
        prof[p]["numeric_near_miss"] = sum(x["numeric_near_miss"] for x in xs)
        prof[p]["fabricated_pages"] = sum(x["fabricated_pages"] for x in xs)
    overall = {}
    for k in keys + ["numeric_near_miss", "fabricated_pages"]:
        v = [pv[k] for pv in prof.values() if pv[k] is not None]
        overall[k] = (sum(v) / len(v) if k in keys else sum(v)) if v else None
    pages = sum(x["n_pages"] for x in per_doc.values())
    wall = sum(x["wall_s"] or 0 for x in per_doc.values())
    overall["sec_per_page"] = wall / pages if pages else None
    longs = [x for d, x in per_doc.items() if docs[d]["profile"] == "long"]
    lp = sum(x["n_pages"] for x in longs)
    overall["sec_per_page_long"] = sum(x["wall_s"] or 0 for x in longs) / lp if lp else None
    costs = [x["cost_usd"] for x in per_doc.values() if x["cost_usd"] is not None]
    overall["cost_per_1k_pages"] = (sum(costs) / pages * 1000) if costs and pages else None
    overall["failures"] = sum(1 for x in per_doc.values() if x["status"] != "ok")
    overall["max_rss_mb"] = max((x["rss_mb"] or 0) for x in per_doc.values())
    overall["pages"] = pages
    counts = {k: sum(x["halluc_counts"][k] for x in per_doc.values()) for k in
              ["hallucinated", "misread", "omitted", "ref_tokens", "hyp_tokens"]}
    overall["counts"] = counts
    return {"overall": overall, "profiles": prof}


def build_report(out_dir: Path = REPORT) -> Path:
    cfg = config.load()
    reg = build(cfg)
    all_docs = {d["id"]: d for d in runner.docs()}
    truths = {i: json.loads(Path(d["pdf"]).with_suffix(".truth.json").read_text()) for i, d in all_docs.items()}
    scores = score.score_all()
    summary = {e: _aggregate(pd, all_docs) for e, pd in scores.items()}

    diffs, thumbs = [], {}
    for e, pd in scores.items():
        if e in ("control_oracle", "liteparse_noocr"):
            continue
        for did, s in pd.items():
            if s["status"] != "ok":
                continue
            worst = max(range(len(s["page_cer"])), key=lambda i: s["page_cer"][i])
            for pg in sorted({0, worst}):
                if s["page_cer"][pg] == 0 and pg != 0:
                    continue
                rec = json.loads((runner.OUT / e / f"{did}.json").read_text())
                hyp = rec["pages"][pg] if pg < len(rec["pages"]) else ""
                key = f"{did}#{pg}"
                if key not in thumbs:
                    thumbs[key] = _thumb(all_docs[did]["pdf"], pg)
                diffs.append({"engine": e, "doc": did, "page": pg + 1, "cer": s["page_cer"][pg], "thumb": key,
                              "seg": _diff(truths[did]["pages"][pg]["text"], hyp)})

    engines = []
    for n, e in reg.items():
        d = e.describe()
        d["ran"] = n in scores
        engines.append(d)
    data = {"meta": runner.system_info(), "engines": engines, "profiles": sorted({d["profile"] for d in all_docs.values()}),
            "docs": [{k: d[k] for k in ("id", "profile", "lang", "n_pages")} for d in all_docs.values()],
            "summary": summary, "perdoc": scores, "diffs": diffs, "thumbs": thumbs}
    out_dir.mkdir(parents=True, exist_ok=True)
    html = (HERE / "template.html").read_text().replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out = out_dir / "index.html"
    out.write_text(html)
    (out_dir / "data.json").write_text(json.dumps({k: v for k, v in data.items() if k != "thumbs"}, ensure_ascii=False))
    return out
