"""One real Nemotron call, before any pipeline is rebuilt around it."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import allocator  # noqa: E402
import brain  # noqa: E402

allocator.load_env()
town = allocator.load_town()
evidence = allocator.build_evidence(town)

print(json.dumps(brain.describe(), indent=2))
print(f"evidence rows: {len(evidence)}")

started = time.time()
proposal, meta = allocator.brain_allocate(town, evidence)
print("\n-- trace --")
print(json.dumps(meta, indent=2, ensure_ascii=False))
print("\n-- proposal --")
print(json.dumps(proposal, indent=2, ensure_ascii=False))
if proposal:
    problems = allocator.validate_proposal(proposal.get("allocation") or {}, town)
    print("\n-- validator --")
    print("PASS" if not problems else "REJECTED: " + "; ".join(problems))
print(f"\nwall clock: {time.time() - started:.2f}s")
