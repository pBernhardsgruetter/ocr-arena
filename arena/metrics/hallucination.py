"""Hallucination = output content that is not on the page.

Token alignment (Levenshtein opcodes over tokens) splits every difference into:
  * deleted  -> omission (silent drop)
  * replaced by a *similar* token -> misread (ordinary OCR error)
  * inserted, or replaced by a *dissimilar* token -> hallucinated
Numbers get extra scrutiny: a number that is not on the page is dangerous, and one that
is a near-miss of a real number (digit swap) is the nastiest, as it looks plausible.
"""
from dataclasses import dataclass, asdict
from rapidfuzz.distance import Levenshtein
from rapidfuzz import fuzz

from .text import tokens, has_digit

SIMILAR = 60  # fuzz.ratio >= this -> misread rather than fabricated


@dataclass
class Halluc:
    ref_tokens: int = 0
    hyp_tokens: int = 0
    hallucinated: int = 0     # fabricated tokens
    omitted: int = 0          # reference tokens missing
    misread: int = 0          # similar-but-wrong tokens
    hyp_numeric: int = 0      # numeric tokens in the output
    numeric_wrong: int = 0    # numeric tokens in output that are not on the page
    numeric_near_miss: int = 0  # ...of which differ from a real number by <=2 chars
    fabricated_page: int = 0  # 1 if text was produced for a page with no text

    def add(self, o: "Halluc"):
        for k, v in asdict(o).items():
            setattr(self, k, getattr(self, k) + v)

    def rates(self) -> dict:
        d = lambda a, b: a / b if b else 0.0
        return {
            "halluc_rate": d(self.hallucinated, self.hyp_tokens),
            "omission_rate": d(self.omitted, self.ref_tokens),
            "numeric_error_rate": d(self.numeric_wrong, self.hyp_numeric),
            "numeric_near_miss": self.numeric_near_miss,
            "fabricated_pages": self.fabricated_page,
        }


def analyze(ref: str, hyp: str) -> Halluc:
    r, h = tokens(ref), tokens(hyp)
    out = Halluc(ref_tokens=len(r), hyp_tokens=len(h))
    if not r:
        if len(h) >= 3:
            out.fabricated_page = 1
        out.hallucinated = len(h)
        out.hyp_numeric = sum(has_digit(t) for t in h)
        out.numeric_wrong = out.hyp_numeric
        return out
    ref_set = set(r)
    ref_nums = [t for t in r if has_digit(t)]
    for tag, i1, i2, j1, j2 in Levenshtein.opcodes(r, h):
        if tag == "delete":
            out.omitted += i2 - i1
        elif tag == "insert":
            out.hallucinated += j2 - j1
        elif tag == "replace":
            rs, hs = r[i1:i2], h[j1:j2]
            for k, ht in enumerate(hs):
                best = max((fuzz.ratio(ht, rt) for rt in rs), default=0)
                if best >= SIMILAR or ht in ref_set:
                    out.misread += 1
                else:
                    out.hallucinated += 1
            if len(rs) > len(hs):
                out.omitted += len(rs) - len(hs)
    for t in h:
        if has_digit(t):
            out.hyp_numeric += 1
            if t not in ref_set:
                out.numeric_wrong += 1
                if any(Levenshtein.distance(t, n) <= 2 for n in ref_nums):
                    out.numeric_near_miss += 1
    return out
