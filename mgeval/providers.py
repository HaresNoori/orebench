"""Model providers.

Live providers call the vendor HTTP APIs with the standard library only (no SDKs), reading
API keys from environment variables at call time. Keys are never logged or written to disk.

Model ids are always supplied by the user (``provider:model_id``); none are hard-coded,
because vendor model names change faster than a benchmark does.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
}


class Provider(Protocol):
    name: str

    def complete(self, system: str, prompt: str, max_tokens: int) -> str: ...


class ProviderError(RuntimeError):
    pass


def _post_json(url: str, headers: dict[str, str], body: dict, timeout: float = 180.0, retries: int = 3) -> dict:
    data = json.dumps(body).encode("utf-8")
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers={"content-type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            last = ProviderError(f"HTTP {exc.code}: {detail}")
            if exc.code not in (408, 429, 500, 502, 503, 504, 529):
                break
        except (urllib.error.URLError, TimeoutError) as exc:
            last = ProviderError(f"network error: {exc}")
        time.sleep(2 ** attempt * 2)
    raise last or ProviderError("request failed")


def _key(provider: str) -> str:
    env = KEY_ENV[provider]
    val = os.environ.get(env)
    if not val:
        raise ProviderError(f"{env} is not set")
    return val


@dataclass
class AnthropicProvider:
    model: str
    temperature: float = 0.0

    @property
    def name(self) -> str:
        return f"anthropic:{self.model}"

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
        out = _post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": _key("anthropic"), "anthropic-version": "2023-06-01"},
            {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": self.temperature,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        return "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text")


@dataclass
class OpenAIProvider:
    model: str
    temperature: float | None = None  # some reasoning models reject temperature

    @property
    def name(self) -> str:
        return f"openai:{self.model}"

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
        body: dict = {
            "model": self.model,
            "max_completion_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }
        if self.temperature is not None:
            body["temperature"] = self.temperature
        out = _post_json(
            "https://api.openai.com/v1/chat/completions",
            {"authorization": f"Bearer {_key('openai')}"},
            body,
        )
        return out["choices"][0]["message"].get("content") or ""


@dataclass
class GoogleProvider:
    model: str
    temperature: float = 0.0

    @property
    def name(self) -> str:
        return f"google:{self.model}"

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
        out = _post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"x-goog-api-key": _key("google")},
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": self.temperature},
            },
        )
        cands = out.get("candidates") or []
        if not cands:
            raise ProviderError(f"no candidates returned: {str(out)[:200]}")
        return "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))


# --------------------------------------------------------------------------
# Offline mock providers for dry runs (no keys, no network)
# --------------------------------------------------------------------------
@dataclass
class MockProvider:
    """Deterministic offline candidate.

    mode="reference": returns the item's reference answer plus correct FINAL_JSON (should
    score close to 100%).
    mode="garbage": returns fluent but irrelevant text and wrong numbers (should score close
    to 0%). Together they show the scorer discriminates.
    """

    mode: str = "reference"
    _item: dict | None = None

    @property
    def name(self) -> str:
        return f"mock:{self.mode}"

    def bind(self, item: dict) -> None:
        self._item = item

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
        item = self._item or {}
        checks = item.get("numeric_checks", [])
        if self.mode == "reference":
            final = {c["name"]: c["value"] for c in checks}
            return item.get("reference_answer", "") + "\n\nFINAL_JSON: " + json.dumps(final)
        if self.mode == "garbage":
            final = {c["name"]: -999999 for c in checks}
            return (
                "Thank you for the question. Market sentiment remains constructive and the team "
                "is experienced, so the outlook is positive overall.\n\nFINAL_JSON: " + json.dumps(final)
            )
        raise ValueError(f"unknown mock mode {self.mode}")


def make_provider(spec: str, temperature: float | None = None) -> Provider:
    """Build a provider from ``provider:model_id`` (e.g. ``openai:<model-id>``) or ``mock:reference``."""
    if ":" not in spec:
        raise ValueError(f"model spec must be provider:model_id, got {spec!r}")
    prov, model = spec.split(":", 1)
    if prov == "mock":
        return MockProvider(mode=model)
    if prov == "anthropic":
        return AnthropicProvider(model, 0.0 if temperature is None else temperature)
    if prov == "openai":
        return OpenAIProvider(model, temperature)
    if prov == "google":
        return GoogleProvider(model, 0.0 if temperature is None else temperature)
    raise ValueError(f"unknown provider {prov!r}; use anthropic, openai, google or mock")


def available_keys() -> dict[str, bool]:
    """Which provider keys are present (booleans only; values are never read out)."""
    return {p: bool(os.environ.get(env)) for p, env in KEY_ENV.items()}
