"""One-off probe: what can these two keys actually reach?

Prints the real model IDs and prices from Token Factory, then spends exactly one
Tavily credit proving the search key works. Deleted after the answer is recorded
in the README - it is not part of the product.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import allocator  # noqa: E402

allocator.load_env()

key = (Path(__file__).resolve().parent.parent / ".env").read_text(encoding="utf-8")
nebius_key = next(line.split("=", 1)[1] for line in key.splitlines() if line.startswith("NEBIUS_API_KEY="))
tavily_key = next(line.split("=", 1)[1] for line in key.splitlines() if line.startswith("TAVILY_API_KEY="))


def get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


print("== Token Factory /v1/models ==")
try:
    data = get(
        "https://api.tokenfactory.nebius.com/v1/models?verbose=true",
        {"Authorization": f"Bearer {nebius_key}", "Accept": "application/json"},
    )
    models = data.get("data", [])
    print(f"reachable: {len(models)} models")
    nvidia = [m for m in models if "nvidia" in m.get("id", "").lower() or "nemotron" in m.get("id", "").lower()]
    print(f"nvidia/nemotron: {len(nvidia)}")
    for model in nvidia:
        price = model.get("pricing") or {}
        print(
            f"  {model.get('id'):<60} ctx={model.get('context_length'):<8} "
            f"in={price.get('prompt')} out={price.get('completion')}"
        )
    print("-- full catalogue (ids only) --")
    for model in models:
        print("  ", model.get("id"))
except Exception as exc:  # noqa: BLE001
    print(f"FAILED: {type(exc).__name__}: {exc}")

print("\n== Tavily /search (1 credit) ==")
try:
    body = json.dumps({
        "query": "NH-544 Kottur Pollachi landslide road status",
        "search_depth": "basic",
        "max_results": 5,
    }).encode()
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=body,
        headers={"Authorization": f"Bearer {tavily_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.load(response)
    print(f"reachable: {len(result.get('results', []))} results")
    for item in result.get("results", []):
        print(f"  [{item.get('score', 0):.2f}] {item.get('url')}")
        print(f"        {item.get('title')}")
except Exception as exc:  # noqa: BLE001
    print(f"FAILED: {type(exc).__name__}: {exc}")
