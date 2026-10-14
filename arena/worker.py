"""Run ONE engine on ONE pdf in an isolated process (so we can time it, kill it, measure RSS)."""
import json
import sys
import time
import traceback

from . import config
from .engines.registry import build


def main(engine_name, pdf, out, n_pages):
    eng = build(config.load())[engine_name]
    t0 = time.perf_counter()
    try:
        res = eng.run(pdf, int(n_pages))
        rec = {"status": "ok", "pages": res.pages, "usage": res.usage, "meta": res.meta}
    except Exception as e:  # noqa: BLE001
        rec = {"status": "error", "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:], "pages": []}
    rec["seconds"] = time.perf_counter() - t0
    json.dump(rec, open(out, "w"), ensure_ascii=False)


if __name__ == "__main__":
    main(*sys.argv[1:5])
