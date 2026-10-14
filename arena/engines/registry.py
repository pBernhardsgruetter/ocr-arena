from .base import Engine
from .liteparse_engine import LiteParseEngine
from .tesseract_engine import TesseractCLI
from .vlm_engine import OpenAICompatVLM, KDLFrontier
from .controls import Oracle, Hallucinator

TYPES = {"openai_vlm": OpenAICompatVLM, "kdl_vllm": KDLFrontier}


def build(cfg: dict) -> dict[str, Engine]:
    ec = cfg.get("engines", {})
    engines: list[Engine] = [
        LiteParseEngine("liteparse_md", "LiteParse + Tesseract (markdown)", mode="markdown",
                        notes="Open-source light variant of LlamaParse. PDFium + bundled Tesseract OCR, markdown output."),
        LiteParseEngine("liteparse_text", "LiteParse + Tesseract (spatial text)", mode="text",
                        notes="Same OCR, layout-preserving text output (columns kept as visual grid)."),
        LiteParseEngine("liteparse_noocr", "LiteParse without OCR", mode="text", ocr=False,
                        notes="Text-layer only. Expected ~0% on scans: proves the customer docs need OCR."),
        LiteParseEngine("liteparse_easyocr", "LiteParse + EasyOCR server", server_url=ec.get("liteparse_easyocr", {}).get("url", "http://localhost:8828/ocr"), lang="de",
                        notes="Needs liteparse/ocr/easyocr server running."),
        LiteParseEngine("liteparse_paddle", "LiteParse + PaddleOCR server", server_url=ec.get("liteparse_paddle", {}).get("url", "http://localhost:8829/ocr"), lang="de",
                        notes="Needs liteparse/ocr/paddleocr server running."),
        TesseractCLI(),
        Oracle(), Hallucinator(),
    ]
    for name, c in ec.items():
        t = c.get("type")
        if t in TYPES:
            engines.append(TYPES[t](name, c))
    # always list the GPU/cloud adapters so the report shows them as skipped with a reason
    names = {e.name for e in engines}
    if "kdl_frontier_nano" not in names:
        engines.append(KDLFrontier("kdl_frontier_nano", {}))
    if "vlm_generic" not in names:
        engines.append(OpenAICompatVLM("vlm_generic", {"label": "Vision LLM (OpenAI-compatible)"}))
    return {e.name: e for e in engines}
