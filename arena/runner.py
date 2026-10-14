"""Matrix runner: engine x document, one isolated process per cell, resumable."""
import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import config
from .engines.registry import build

ROOT = config.ROOT
CORPUS = ROOT / "corpus"
OUT = ROOT / "results" / "outputs"


def docs(corpus: Path = CORPUS, profiles=None) -> list[dict]:
    ds = []
    for t in sorted(corpus.glob("*.truth.json")):
        m = json.loads(t.read_text())
        if profiles and m["profile"] not in profiles:
            continue
        ds.append({"id": m["id"], "profile": m["profile"], "lang": m["lang"], "n_pages": m["n_pages"],
                   "pdf": str(t.with_name(t.name.replace(".truth.json", ".pdf")))})
    return ds


def _run_cell(engine: str, doc: dict, out: Path, timeout: float) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    cmd = [sys.executable, "-W", "ignore", "-m", "arena.worker", engine, doc["pdf"], str(tmp), str(doc["n_pages"])]
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)
    status, rss = "ok", 0.0
    while True:
        pid, st, ru = os.wait4(p.pid, os.WNOHANG)
        if pid:
            rss = ru.ru_maxrss / 1024  # KiB -> MiB (Linux)
            break
        if time.perf_counter() - t0 > timeout:
            os.killpg(p.pid, signal.SIGKILL)
            os.wait4(p.pid, 0)
            status = "timeout"
            break
        time.sleep(0.2)
    wall = time.perf_counter() - t0
    if status == "ok" and tmp.exists():
        rec = json.loads(tmp.read_text())
    elif status == "timeout":
        rec = {"status": "timeout", "pages": [], "error": f"killed after {timeout:.0f}s", "seconds": wall}
    else:
        err = (p.stderr.read().decode(errors="ignore")[-800:] if p.stderr else "")
        rec = {"status": "error", "pages": [], "error": f"worker crashed: {err}", "seconds": wall}
    tmp.unlink(missing_ok=True)
    rec.update(wall_s=wall, rss_mb=rss, n_pages=doc["n_pages"], finished=time.strftime("%Y-%m-%d %H:%M:%S"))
    out.write_text(json.dumps(rec, ensure_ascii=False))
    return rec


def run(engines: list[str] | None, profiles=None, force=False, retry_failed=False, max_pages=None, log=print):
    cfg = config.load()
    reg = build(cfg)
    names = engines or [n for n, e in reg.items() if e.available()[0]]
    todo = docs(profiles=profiles)
    for n in names:
        ok, why = reg[n].available()
        if not ok:
            log(f"[skip] {n}: {why}")
            continue
        for d in todo:
            out = OUT / n / f"{d['id']}.json"
            if out.exists() and not force:
                prev = json.loads(out.read_text())
                if prev.get("status") == "ok" or not retry_failed:
                    log(f"[have] {n:22s} {d['id']}")
                    continue
            tmo = cfg["timeouts"]["base_s"] + cfg["timeouts"]["per_page_s"] * d["n_pages"]
            rec = _run_cell(n, d, out, tmo)
            log(f"[{rec['status']:7s}] {n:22s} {d['id']:24s} {rec['n_pages']:4d}p {rec['seconds']:7.1f}s "
                f"{rec['rss_mb']:6.0f}MB " + (rec.get("error") or "")[:120])


def system_info() -> dict:
    cpu = "?"
    try:
        cpu = next(l.split(":")[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name"))
    except Exception:  # noqa: BLE001
        pass
    mem = "?"
    try:
        mem = f"{int(open('/proc/meminfo').readline().split()[1]) / 1048576:.0f} GB"
    except Exception:  # noqa: BLE001
        pass
    try:
        from importlib.metadata import version
        lp = version("liteparse")
    except Exception:  # noqa: BLE001
        lp = "?"
    return {"cpu": cpu, "cores": os.cpu_count(), "ram": mem, "gpu": "none", "os": platform.platform(),
            "python": platform.python_version(), "liteparse": lp, "date": time.strftime("%Y-%m-%d %H:%M")}
