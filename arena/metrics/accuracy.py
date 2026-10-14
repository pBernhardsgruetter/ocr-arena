from rapidfuzz.distance import Levenshtein
from rapidfuzz import fuzz

from .text import clean, tokens


def cer(ref: str, hyp: str) -> float:
    ref, hyp = clean(ref), clean(hyp)
    if not ref:
        return 0.0 if not hyp else 1.0
    return min(1.0, Levenshtein.distance(ref, hyp) / len(ref))


def wer(ref: str, hyp: str) -> float:
    r, h = tokens(ref), tokens(hyp)
    if not r:
        return 0.0 if not h else 1.0
    return min(1.0, Levenshtein.distance(r, h) / len(r))


def region_match(region_text: str, hyp: str) -> float:
    """How well a known region (e.g. a handwritten field) is found anywhere in the output.

    1.0 = verbatim present, 0.0 = absent. Output has no region boundaries, so we take
    the best fuzzy window.
    """
    reg, hyp = clean(region_text), clean(hyp)
    if not reg:
        return 1.0
    if not hyp:
        return 0.0
    return fuzz.partial_ratio(reg, hyp) / 100.0
