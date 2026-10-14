"""Structure metrics: table cell F1 and reading order. A ParseBench-style subset,
not the official scorer."""
import re
from rapidfuzz import fuzz

from .text import normalize

_SPLIT = re.compile(r"\s{2,}|\t")


def _cells_of_line(line: str) -> list[str]:
    line = line.strip()
    if "|" in line:
        return [normalize(c) for c in line.strip("|").split("|")]
    return [normalize(c) for c in _SPLIT.split(line)]


def hyp_rows(text: str) -> list[list[str]]:
    rows = []
    for line in (text or "").splitlines():
        if not line.strip() or re.fullmatch(r"[\s|:\-]+", line):
            continue
        cells = [c for c in _cells_of_line(line) if c]
        if cells:
            rows.append(cells)
    return rows


def table_f1(truth_rows: list[list[str]], hyp_text: str) -> float:
    """Cell-level F1. Each truth row is matched to its most similar output row; a cell
    counts when it equals the output cell in the same column."""
    hrows = hyp_rows(hyp_text)
    n_truth = sum(len(r) for r in truth_rows)
    if not n_truth:
        return 1.0
    if not hrows:
        return 0.0
    used, tp = set(), 0
    for tr in truth_rows:
        joined = " ".join(tr)
        best, bi = 0.0, -1
        for i, hr in enumerate(hrows):
            if i in used:
                continue
            s = fuzz.ratio(joined, " ".join(hr))
            if s > best:
                best, bi = s, i
        if bi < 0 or best < 50:
            continue
        used.add(bi)
        hr = hrows[bi]
        tp += sum(1 for c, hc in zip(tr, hr) if normalize(c) == hc)
    # precision over table-like output only: matched rows + other rows that look tabular (>=3 cells);
    # prose lines elsewhere on the page must not count against the table
    n_hyp = sum(len(r) for i, r in enumerate(hrows) if i in used or len(r) >= 3)
    p = tp / n_hyp if n_hyp else 0.0
    r = tp / n_truth
    return 2 * p * r / (p + r) if p + r else 0.0


def reading_order(paragraphs: list[str], hyp_text: str) -> float | None:
    """Fraction of paragraph pairs the output keeps in the right order (1.0 = perfect)."""
    pos = []
    hyp = normalize(hyp_text)
    for p in paragraphs:
        p = normalize(p)
        if len(p) < 20:
            continue
        al = fuzz.partial_ratio_alignment(p, hyp)
        if al and al.score >= 70:
            pos.append(al.dest_start)
    if len(pos) < 2:
        return None
    conc = tot = 0
    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            tot += 1
            conc += pos[i] < pos[j]
    return conc / tot
