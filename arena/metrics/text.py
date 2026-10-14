"""Text normalisation + tokenisation shared by all metrics."""
import re
import unicodedata

_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"\S+")
# markdown decoration that an engine may add but is not page content
_MD_DECOR = re.compile(r"^\s*(#{1,6}\s+|[-*+]\s+|>\s+)", re.M)
_MD_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", re.M)
_PIPE = re.compile(r"\|")
_IMG_PLACEHOLDER = re.compile(r"!\[[^\]]*\]\([^)]*\)|<!--.*?-->", re.S)
_BOLD = re.compile(r"(\*\*|__)")
_ESC = re.compile(r"\\([|*_#\[\]()<>`~!.-])")


def strip_markdown(s: str) -> str:
    s = _ESC.sub(r"\1", s)
    s = _IMG_PLACEHOLDER.sub(" ", s)
    s = _MD_TABLE_SEP.sub(" ", s)
    s = _PIPE.sub(" ", s)
    s = _MD_DECOR.sub("", s)
    return _BOLD.sub("", s)


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    return _WS.sub(" ", s).strip()


def clean(s: str) -> str:
    return normalize(strip_markdown(s or ""))


def tokens(s: str) -> list[str]:
    return _TOKEN.findall(clean(s))


def has_digit(tok: str) -> bool:
    return any(c.isdigit() for c in tok)
