import json, pymupdf as fitz
from arena.docgen.build import build_corpus


def test_deterministic_and_scanned(tmp_path):
    a = build_corpus(tmp_path / "a", seed=1, per_profile=1, profiles=["mixed"], langs=("de",))
    b = build_corpus(tmp_path / "b", seed=1, per_profile=1, profiles=["mixed"], langs=("de",))
    assert [p["text"] for p in a[0]["pages"]] == [p["text"] for p in b[0]["pages"]]
    pdf = fitz.open(tmp_path / "a" / "mixed_de_00.pdf")
    assert len(pdf) == a[0]["n_pages"]
    assert all(not pg.get_text().strip() for pg in pdf), "scans must have no text layer"
    kinds = {r["kind"] for pg in a[0]["pages"] for r in pg["regions"]}
    assert {"printed", "table"} <= kinds
