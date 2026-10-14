import argparse
import json
from pathlib import Path

from . import config, runner
from .docgen.build import build_corpus, PROFILES
from .engines.registry import build


def main(argv=None):
    ap = argparse.ArgumentParser(prog="arena", description="OCR benchmark arena")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen", help="generate the synthetic scanned corpus")
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--per-profile", type=int, default=2)
    g.add_argument("--long-pages", type=int, default=100)
    g.add_argument("--profiles", nargs="*", choices=list(PROFILES))
    sub.add_parser("doctor", help="show which engines are runnable")
    r = sub.add_parser("run", help="run engines over the corpus (resumable)")
    r.add_argument("--engines", nargs="*")
    r.add_argument("--profiles", nargs="*")
    r.add_argument("--force", action="store_true")
    r.add_argument("--retry-failed", action="store_true")
    rp = sub.add_parser("report", help="score + render results/report/index.html")
    rp.add_argument("--open", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "gen":
        m = build_corpus(runner.CORPUS, a.seed, a.per_profile, a.long_pages, a.profiles)
        print(f"generated {len(m)} documents ({sum(d['n_pages'] for d in m)} pages) in {runner.CORPUS}")
    elif a.cmd == "doctor":
        for e in build(config.load()).values():
            d = e.describe()
            print(f"{'OK  ' if d['available'] else 'SKIP'} {d['name']:22s} {d['reason'] if not d['available'] else ''}")
    elif a.cmd == "run":
        runner.run(a.engines, a.profiles, a.force, a.retry_failed)
    elif a.cmd == "report":
        from .report.build import build_report
        p = build_report()
        print(f"report: {p}")
        if a.open:
            import webbrowser
            webbrowser.open(p.as_uri())


if __name__ == "__main__":
    main()
