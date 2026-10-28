"""BRAIN - one provider seam, so the engine never knows who is thinking.

The deterministic core (A*, the 70/30 validator, the hash chain, the gate) does
not import this file. Only the three places that need a language model do:
allocation, the 8-locale payloads, and spoken-intent classification.

One provider, because this repo was built for one hackathon:

    LLM_PROVIDER=nebius   Nebius Token Factory, /chat/completions

The Nebius side is not a URL swap. The four model IDs below were read from
``GET /v1/models`` on 2026-10-28, together with their per-token prices, and are
recorded here so the spend ledger can price a call without guessing:

    nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B    $0.06 / $0.24 per M tokens
    nvidia/Nemotron-3_5-Lightning            $0.06 / $0.24 per M tokens
    nvidia/nemotron-3-super-120b-a12b        $0.30 / $0.90 per M tokens
    nvidia/Nemotron-3-Ultra-550b-a55b        $1.00 / $3.00 per M tokens

Three tiers, matching NVIDIA's own guidance: Nano for volume, Super for review,
Ultra for the one decision that matters. If a tier is not configured the code
falls back to a cheaper one rather than silently calling nothing.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

PROVIDERS = ("nebius",)

# USD per token, read from the live catalogue rather than typed from memory.
PRICES: dict[str, tuple[float, float]] = {
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": (0.00000006, 0.00000024),
    "nvidia/Nemotron-3_5-Lightning": (0.00000006, 0.00000024),
    "nvidia/nemotron-3-super-120b-a12b": (0.0000003, 0.0000009),
    "nvidia/Nemotron-3-Ultra-550b-a55b": (0.000001, 0.000003),
}

TIER_ENV = {
    "fast": "NEBIUS_MODEL_FAST",
    "deep": "NEBIUS_MODEL_DEEP",
    "decision": "NEBIUS_MODEL_DECISION",
}

DEFAULTS = {
    "fast": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    "deep": "nvidia/nemotron-3-super-120b-a12b",
    "decision": "nvidia/Nemotron-3-Ultra-550b-a55b",
}


def provider() -> str:
    value = os.environ.get("LLM_PROVIDER", "nebius").strip().lower()
    return value if value in PROVIDERS else "nebius"


def label() -> str:
    return "Nebius Token Factory"


def model(tier: str = "deep") -> str:
    """Resolve a tier to a real model ID, with a cheaper fallback, never a guess."""
    tier = tier if tier in DEFAULTS else "deep"
    order = {"decision": ("decision", "deep", "fast"), "deep": ("deep", "fast"), "fast": ("fast",)}
    for candidate in order[tier]:
        value = os.environ.get(TIER_ENV[candidate], "").strip()
        if value:
            return value
        # Defaults are only used when nothing is configured for that tier.
        if candidate == tier:
            return DEFAULTS[tier]
    return DEFAULTS["fast"]


def endpoint() -> str:
    return os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/").rstrip("/")


def key() -> str:
    return os.environ.get("NEBIUS_API_KEY", "")


def configured() -> bool:
    if os.environ.get("LIFELINE_OFFLINE", "0") == "1":
        return False
    return bool(endpoint() and key())


def price_usd(usage: dict | None, model_id: str) -> float:
    """Cost a response from its real token counts; 0 when the model is unpriced."""
    if not usage:
        return 0.0
    prompt_rate, completion_rate = PRICES.get(model_id, (0.0, 0.0))
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return prompt_tokens * prompt_rate + completion_tokens * completion_rate


def _parse_json(text: str | None) -> dict:
    if not text:
        return {}
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    for candidate in (cleaned, cleaned[cleaned.find("{"): cleaned.rfind("}") + 1] if "{" in cleaned else ""):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return {}


def chat(
    prompt: str,
    tier: str = "deep",
    system: str = "You output strict JSON only.",
    timeout: float = 90.0,
    max_tokens: int = 3000,
    reasoning_effort: str | None = None,
) -> dict:
    """One completion, normalised. Never raises: the caller reads ``status``."""
    model_id = model(tier)
    meta: dict = {
        "provider": label(),
        "model": model_id,
        "endpoint": endpoint(),
        "status": "unavailable",
        "latency_s": None,
        "text": None,
        "usage": None,
        "cost_usd": 0.0,
        "detail": "",
    }
    if os.environ.get("LIFELINE_OFFLINE", "0") == "1":
        meta["detail"] = "LIFELINE_OFFLINE=1"
        return meta
    if not configured():
        meta["detail"] = "NEBIUS_BASE_URL and NEBIUS_API_KEY must be set"
        return meta

    payload: dict = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens,
    }
    if reasoning_effort:
        # Token Factory accepts it. It is not a token cap: measured here, Nano
        # still spent 6,000 tokens and returned empty content on a draft, so the
        # tier choice is what actually bounds cost and latency.
        payload["reasoning_effort"] = reasoning_effort

    started = time.time()
    try:
        request = urllib.request.Request(
            endpoint() + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key()}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        # One retry without response_format: a gateway that rejects the field is
        # not a reason to lose the call, and the prompt already says "JSON only".
        if "response_format" in detail:
            payload.pop("response_format", None)
            try:
                request = urllib.request.Request(
                    endpoint() + "/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key()}"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
            except Exception as retry_exc:  # noqa: BLE001
                meta["status"] = "error"
                meta["detail"] = f"{type(retry_exc).__name__}: {retry_exc}"
                meta["latency_s"] = round(time.time() - started, 2)
                return meta
        else:
            meta["status"] = "error"
            meta["detail"] = f"HTTP {exc.code}: {detail}"
            meta["latency_s"] = round(time.time() - started, 2)
            return meta
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        meta["status"] = "error"
        meta["detail"] = f"{type(exc).__name__}: {exc}"
        meta["latency_s"] = round(time.time() - started, 2)
        return meta

    meta["latency_s"] = round(time.time() - started, 2)
    meta["usage"] = body.get("usage")
    meta["cost_usd"] = price_usd(meta["usage"], model_id)
    try:
        meta["text"] = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        meta["status"] = "error"
        meta["detail"] = "no choices[0].message.content"
        return meta

    if not (meta["text"] or "").strip():
        finish = body["choices"][0].get("finish_reason") if body.get("choices") else None
        meta["status"] = "error"
        meta["detail"] = f"empty content: finish_reason={finish} - raise max_tokens"
        return meta

    meta["status"] = "answered"
    return meta


def describe() -> dict:
    """What the UI and the artefact should say, in one place."""
    return {
        "provider": provider(),
        "label": label(),
        "tiers": {tier: model(tier) for tier in DEFAULTS},
        "configured": configured(),
    }
