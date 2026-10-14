# OCR Arena

Benchmarks OCR / document-parsing engines on **scanned documents without a text layer**
(printed text, tables, photos, handwriting), German + English, and measures what matters for
high-stakes documents: **accuracy, hallucinations, wrong numbers, speed, cost, structure**.

```bash
uv venv --python 3.12 .venv && uv pip install -e .   # once
.venv/bin/arena doctor            # which engines can run here, and why others can't
.venv/bin/arena gen               # synthetic scanned corpus (--long-pages 500 for a 500-page doc)
.venv/bin/arena run               # all available engines; resumable (--force, --retry-failed, --engines a b)
.venv/bin/arena report --open     # results/report/index.html
```

## Engines

| Engine | Needs | Status here |
|---|---|---|
| `liteparse_md`, `liteparse_text` | `pip install liteparse` (bundles Tesseract) | runs |
| `liteparse_noocr` | – | runs (proves OCR is needed) |
| `tesseract` | `apt install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng` | skipped until installed |
| `liteparse_easyocr` / `_paddle` | start servers from `liteparse/ocr/` | skipped until running |
| `kdl_frontier_nano` | GPU box running vLLM, see `arena.toml.example` | skipped until configured |
| `vlm_generic` | any OpenAI-compatible vision endpoint | skipped until configured |
| `control_oracle`, `control_hallucinator` | – | always run: they validate the metrics |

Add an engine: subclass `arena.engines.base.Engine` (`available()`, `run(pdf, n_pages) -> EngineResult`),
register it in `arena/engines/registry.py`.

KDL on Windows/WSL2 (benchmarked on an RTX A4000, 16 GB):
```bash
docker run -d --name kdl --gpus all --ipc=host -p 8000:8000 -v hf-cache:/root/.cache/huggingface vllm/vllm-openai:latest   --model KDLAI/KDL-Frontier-Parser-nano --trust-remote-code --limit-mm-per-prompt '{"image":1}' --max-model-len 8192
```
then `cp arena.toml.example arena.toml` (point `base_url` at `localhost:8000`) and `arena run --engines kdl_frontier_nano`.

## Metrics (see the report's *Method* section)
CER/WER, fabricated-token rate, omission rate, wrong-number rate and digit near-misses, handwriting
recall, table cell F1, reading order, sec/page, 500-page ETA, peak RAM, $/1k pages, failures.

## Caveats
Synthetic corpus: exact truth, but simulated scans/handwriting. Real customer pages will score worse;
treat results as relative. To add real documents, put `x.pdf` + `x.truth.json` (same schema as the
generated ones) into `corpus/`. KDL is AGPL-3.0; its adapter sends whole pages (the model card describes a
layout-crop pipeline), so treat its score as a lower bound.

Layout: `arena/docgen` (corpus) · `arena/engines` · `arena/metrics` · `arena/runner.py` (isolated process per engine×doc)
· `arena/score.py` (re-scoring never re-runs engines) · `arena/report` (single-file HTML).
