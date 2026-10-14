"""OpenAI-compatible vision endpoints: generic VLM (GPT-style / Claude via proxy / vLLM) and the
KDL-Frontier-Parser. Skipped unless an endpoint is configured in arena.toml."""
import base64
import os
from concurrent.futures import ThreadPoolExecutor

import httpx

from .base import Engine, EngineResult, render_pages

PROMPT = ("Transcribe all text on this page exactly as written, in reading order, as Markdown "
          "(tables as Markdown tables). Do not summarise, translate, correct or add anything. "
          "Reproduce numbers character by character. If a region is illegible write [illegible]. "
          "If the page contains no text, return nothing.")


class OpenAICompatVLM(Engine):
    kind = "api"

    def __init__(self, name, cfg):
        super().__init__(cfg)
        self.name = name
        self.label = cfg.get("label", name)
        self.notes = cfg.get("notes", "Vision LLM transcription: the hallucination-prone class this arena guards against.")

    def _headers(self):
        key = os.environ.get(self.cfg.get("api_key_env", ""), "")
        return {"Authorization": f"Bearer {key}"} if key else {}

    def available(self):
        if not self.cfg.get("base_url") or not self.cfg.get("model"):
            return False, "no base_url/model configured in arena.toml"
        env = self.cfg.get("api_key_env")
        if env and not os.environ.get(env):
            return False, f"env var {env} not set"
        return True, "ok"

    def _payload(self, b64):
        return {**self.cfg.get("extra_body", {}), "model": self.cfg["model"], "temperature": 0, "max_tokens": self.cfg.get("max_tokens", 4096),
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": self.cfg.get("prompt", PROMPT)}]}]}

    def _page(self, png: bytes):
        b64 = base64.b64encode(png).decode()
        r = httpx.post(self.cfg["base_url"].rstrip("/") + "/chat/completions", json=self._payload(b64),
                       headers=self._headers(), timeout=self.cfg.get("request_timeout_s", 300))
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"] or "", j.get("usage", {})

    def run(self, pdf_path, n_pages):
        imgs = render_pages(pdf_path, self.cfg.get("dpi", 150))
        with ThreadPoolExecutor(self.cfg.get("concurrency", 4)) as ex:
            res = list(ex.map(self._page, imgs))
        tin = sum(u.get("prompt_tokens", 0) for _, u in res)
        tout = sum(u.get("completion_tokens", 0) for _, u in res)
        cost = tin * self.cfg.get("price_in_per_m", 0) / 1e6 + tout * self.cfg.get("price_out_per_m", 0) / 1e6
        return EngineResult(pages=[t for t, _ in res], usage={"in_tokens": tin, "out_tokens": tout, "cost_usd": cost})


class KDLFrontier(OpenAICompatVLM):
    """KDLAI/KDL-Frontier-Parser-nano served by vLLM. EXPERIMENTAL: the model card describes a
    layout-detect -> crop -> per-region prompt pipeline; this adapter sends whole pages with the
    'Text Recognition:' prompt, which is a simplification. Greedy decoding, thinking off."""

    def __init__(self, name, cfg):
        cfg = {"label": "KDL-Frontier-Parser-nano (full-page, experimental)", "prompt": "Text Recognition:",
               "notes": "Leaderboard #1 on ParseBench. AGPL-3.0, 1.2B params, needs a GPU (vLLM).", **cfg}
        super().__init__(name, cfg)

    def _payload(self, b64):
        p = super()._payload(b64)
        p["chat_template_kwargs"] = {"enable_thinking": False}
        p["skip_special_tokens"] = False
        return p
