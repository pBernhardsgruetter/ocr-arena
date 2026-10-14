"""Build scanned (image-only, no text layer) PDFs + truth.json for each profile."""
import json
import random
from pathlib import Path

import pymupdf

from . import content as C
from .render import Page, degrade, to_jpeg, find_font, PRINTED, HAND

# profile -> (degradation level, dpi, jpeg quality)
PROFILES = {
    "clean":       ("clean", 200, 90),
    "degraded":    ("scan", 150, 70),
    "handwritten": ("scan", 200, 80),
    "mixed":       ("scan", 200, 75),
    "bad_scan":    ("bad", 150, 55),
    "long":        ("scan", 150, 70),
}


def _page_letter(p: Page, r, lang):
    p.heading(C.heading(r, lang))
    while p.room(260):
        p.paragraph(C.paragraph(r, lang))


def _page_form(p: Page, r, lang):
    p.heading("Antragsformular" if lang == "de" else "Application form")
    p.paragraph(C.paragraph(r, lang, 2))
    L = (["Name:", "Adresse:", "Datum:", "Betrag in CHF:", "Bemerkung:"] if lang == "de"
         else ["Name:", "Address:", "Date:", "Amount in CHF:", "Remark:"])
    K = ["name", "addr", "date", "amount", "note"]
    for _ in range(3):
        for lab, k in zip(L, K):
            p.handwritten(lab, C.hand_value(r, k))
        p.skip(30)
    p.paragraph(C.paragraph(r, lang, 2))


def _page_mixed(p: Page, r, lang):
    p.heading(C.heading(r, lang))
    p.paragraph(C.paragraph(r, lang, 3))
    p.table(C.table(r, lang))
    p.picture()
    p.paragraph(C.paragraph(r, lang, 3))
    p.handwritten("Notiz:" if lang == "de" else "Note:", C.hand_value(r, "note"))
    while p.room(300):
        p.paragraph(C.paragraph(r, lang, 3))


def _page_image_only(p: Page, r, lang):
    p.picture(0.35)  # a photo-only page: correct output is (almost) nothing


def _page_long(p: Page, r, lang):
    p.heading(C.heading(r, lang))
    p.paragraph(C.paragraph(r, lang, 4))
    p.table(C.table(r, lang, r.randint(3, 6)))
    p.paragraph(C.paragraph(r, lang, 3))


LAYOUTS = {
    "clean": [_page_letter, _page_mixed],
    "degraded": [_page_letter, _page_mixed],
    "bad_scan": [_page_letter, _page_mixed],
    "handwritten": [_page_form],
    "mixed": [_page_mixed, _page_mixed, _page_letter, _page_image_only],
    "long": [_page_long],
}


def build_doc(out_dir: Path, profile: str, idx: int, lang: str, pages: int, seed: int) -> dict:
    level, dpi, q = PROFILES[profile]
    doc_id = f"{profile}_{lang}_{idx:02d}"
    r = random.Random(f"{seed}/{doc_id}")
    scale = 1.0 if dpi >= 200 else 0.75  # render smaller when output dpi is low (speed)
    pdf = pymupdf.open()
    truth_pages = []
    layouts = LAYOUTS[profile]
    for n in range(pages):
        p = Page(r, scale=scale)
        layouts[n % len(layouts)](p, r, lang)
        img = degrade(p.img, r, level)
        jpg = to_jpeg(img, dpi, q)
        page = pdf.new_page(width=595.28, height=841.89)
        page.insert_image(page.rect, stream=jpg)
        regions = p.truth
        text = "\n".join(x["text"] for x in regions if x["text"])
        truth_pages.append({"page": n + 1, "text": text, "regions": regions,
                            "blank": not text.strip()})
    pdf.save(out_dir / f"{doc_id}.pdf", deflate=True)
    meta = {"id": doc_id, "profile": profile, "lang": lang, "n_pages": pages, "dpi": dpi,
            "degradation": level, "pages": truth_pages,
            "fonts": {"printed": Path(find_font(PRINTED)).name, "handwriting": Path(find_font(HAND)).name},
            "synthetic": True}
    (out_dir / f"{doc_id}.truth.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


def build_corpus(out_dir: Path, seed=42, per_profile=2, long_pages=100, profiles=None, langs=("de", "en")):
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for prof in profiles or PROFILES:
        n_docs = 1 if prof == "long" else per_profile
        for i in range(n_docs):
            lang = langs[0] if prof == "long" else langs[i % len(langs)]
            pages = long_pages if prof == "long" else (4 if prof == "mixed" else 2)
            made.append(build_doc(out_dir, prof, i, lang, pages, seed))
    return made
