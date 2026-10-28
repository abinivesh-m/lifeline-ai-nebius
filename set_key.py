"""Rotate NEBIUS_API_KEY in .env without ever hardcoding a secret.

The key is read from the environment or prompted for with echo off, written
only to the gitignored .env, and then verified with one tiny live call so a
typo fails here instead of during the demo.

Run:
    python set_key.py                    # reads LIFELINE_NEW_NEBIUS_KEY
    python set_key.py --prompt           # type it, input hidden
    python set_key.py --verify-only      # just check the key already in .env
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

ENV_PATH = Path(__file__).with_name(".env")
VAR = "NEBIUS_API_KEY"


def read_env(path: Path = ENV_PATH) -> dict[str, str]:
    pairs: dict[str, str] = {}
    if not path.exists():
        return pairs
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        pairs[key.strip()] = value.strip()
    return pairs


def write_key(new: str, path: Path = ENV_PATH) -> int:
    """Rewrite every ``NEBIUS_API_KEY=`` line, or append one. Returns hits."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    hits = 0
    out: list[str] = []
    for line in lines:
        if line.strip().startswith(f"{VAR}="):
            out.append(f"{VAR}={new}")
            hits += 1
        else:
            out.append(line)
    if not hits:
        out.append(f"{VAR}={new}")
        hits = 1
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return hits


def verify() -> int:
    """One cheap call through brain.py, so a broken key is found now."""
    import allocator
    import brain

    allocator.load_env()
    if not brain.configured():
        print(f"  {VAR} or NEBIUS_BASE_URL is not set", file=sys.stderr)
        return 2
    result = brain.chat('Reply with JSON only: {"ok": true}', tier="fast", max_tokens=200)
    if result["status"] != "answered":
        print(f"  call failed: {result['detail']}", file=sys.stderr)
        return 1
    print(
        f"  key works · {result['model']} · {result['latency_s']} s · "
        f"${result['cost_usd']:.6f}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Rotate {VAR} in .env")
    parser.add_argument("--prompt", action="store_true", help="type the key, input hidden")
    parser.add_argument("--verify-only", action="store_true", help="check the key already on disk")
    args = parser.parse_args(argv)

    if not args.verify_only:
        key = os.environ.get("LIFELINE_NEW_NEBIUS_KEY", "").strip()
        if not key and args.prompt:
            key = getpass.getpass(f"New {VAR} (input hidden): ").strip()
        if not key:
            print(
                f"  no key supplied - set LIFELINE_NEW_NEBIUS_KEY or pass --prompt",
                file=sys.stderr,
            )
            return 2
        hits = write_key(key)
        print(f"  rewrote {hits} {VAR} line(s) in .env (gitignored)")
        os.environ[VAR] = key

    return verify()


if __name__ == "__main__":
    sys.exit(main())
