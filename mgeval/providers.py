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
# Subscription command-line agents (no API key; uses the CLI's own sign-in).
# Settings are less controlled than the APIs: the CLI's own system prompt,
# user-level instructions and default reasoning effort apply.
# --------------------------------------------------------------------------
@dataclass
class CodexCLIProvider:
    """OpenAI Codex CLI (`codex exec`), read-only sandbox, run in an empty directory."""

    model: str = "default"
    reasoning_effort: str | None = None
    binary: str | None = None
    reported_model: str | None = None

    @property
    def name(self) -> str:
        return f"codex-cli:{self.reported_model or self.model}"

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
        import re
        import shutil
        import subprocess
        import tempfile

        exe = self.binary or os.environ.get("MGEVAL_CODEX_BIN") or shutil.which("codex")
        if not exe:
            raise ProviderError("codex CLI not found (set MGEVAL_CODEX_BIN)")
        with tempfile.TemporaryDirectory() as work:
            last = os.path.join(work, "last.txt")
            cmd = [exe, "exec", "--skip-git-repo-check", "--sandbox", "read-only", "--ephemeral",
                   "-C", work, "-o", last]
            if self.model != "default":
                cmd += ["-m", self.model]
            if self.reasoning_effort:
                cmd += ["-c", f'model_reasoning_effort="{self.reasoning_effort}"']
            cmd.append("-")
            text = f"{system}\n\nDo not use any tools, files or web access. Answer directly.\n\n{prompt}"
            try:
                proc = subprocess.run(cmd, input=text, capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=1800)
            except subprocess.TimeoutExpired as exc:
                raise ProviderError("codex CLI timed out") from exc
            m = re.search(r"^model:\s*(\S+)", proc.stdout + "\n" + proc.stderr, re.MULTILINE)
            if m:
                self.reported_model = m.group(1)
            if not os.path.exists(last):
                raise ProviderError(f"codex CLI failed (rc={proc.returncode}): {proc.stderr[-300:]}")
            with open(last, encoding="utf-8", errors="replace") as fh:
                return fh.read()


@dataclass
class ClaudeCLIProvider:
    """Claude Code headless mode (`claude -p`), all built-in tools disabled."""

    model: str = "default"
    binary: str | None = None

    @property
    def name(self) -> str:
        return f"claude-cli:{self.model}"

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
        import shutil
        import subprocess
        import tempfile

        exe = self.binary or os.environ.get("MGEVAL_CLAUDE_BIN") or shutil.which("claude")
        if not exe:
            raise ProviderError("claude CLI not found (set MGEVAL_CLAUDE_BIN)")
        cmd = [exe, "-p", "--tools", "", "--system-prompt", system, "--output-format", "json"]
        if self.model != "default":
            cmd += ["--model", self.model]
        with tempfile.TemporaryDirectory() as work:
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=1800, cwd=work)
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"claude CLI gave no JSON (rc={proc.returncode})") from exc
        if out.get("is_error"):
            raise ProviderError(f"claude CLI error: {str(out.get('result'))[:200]}")
        return out.get("result", "")


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
        return self.respond_item(self._item or {})

    def respond_item(self, item: dict) -> str:
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


@dataclass
class ReplayProvider:
    """Replays answers collected elsewhere (for example from an agent session), so they can be
    scored with the same judge and numeric checks. File: JSONL with item_id and response."""

    path: str
    label: str

    def __post_init__(self) -> None:
        self._answers: dict[str, str] = {}
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    self._answers[rec["item_id"]] = rec["response"]

    @property
    def name(self) -> str:
        return self.label

    def respond_item(self, item: dict) -> str:
        if item["id"] not in self._answers:
            raise ProviderError(f"no recorded answer for {item['id']}")
        return self._answers[item["id"]]

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
        raise ProviderError("replay provider answers per item only")


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
    if prov == "codex-cli":
        name, _, effort = model.partition("@")  # e.g. codex-cli:default@medium
        return CodexCLIProvider(name or "default", effort or None)
    if prov == "claude-cli":
        return ClaudeCLIProvider(model or "default")
    raise ValueError(f"unknown provider {prov!r}; use anthropic, openai, google, codex-cli, claude-cli or mock")


def available_keys() -> dict[str, bool]:
    """Which provider keys are present (booleans only; values are never read out)."""
    return {p: bool(os.environ.get(env)) for p, env in KEY_ENV.items()}
