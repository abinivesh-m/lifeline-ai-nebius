"""Print the exact numbers the README quotes, straight from the artefacts."""

import collections
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent

led = json.loads((root / "credit_usage.json").read_text(encoding="utf-8"))
rows = collections.Counter()
calls = collections.Counter()
cost = collections.Counter()
for entry in led["entries"]:
    rows[entry["model"]] += 1
    calls[entry["model"]] += entry["calls"]
    cost[entry["model"]] += entry["cost_usd"]

print("=== inference ledger ===")
for model in sorted(rows):
    print(f"  {model:<10} rows={rows[model]:3d}  calls={calls[model]:4d}  ${cost[model]:.6f}")
print(f"  total rows={len(led['entries'])}  ${sum(cost.values()):.6f}")

proof = json.loads((root / "artifacts" / "nebius_proof.json").read_text(encoding="utf-8"))
print("\n=== nebius_proof.json ===")
print("  keys:", list(proof))
print("  totals:", json.dumps(proof.get("totals"), indent=2)[:600])
print("  tiers:", json.dumps(proof.get("tiers")))

tav = json.loads((root / "artifacts" / "tavily_usage.json").read_text(encoding="utf-8"))
print("\n=== tavily_usage.json ===")
print(" ", json.dumps(tav)[:400])

ui = json.loads((root / "ui" / "public" / "data" / "lifeline.json").read_text(encoding="utf-8"))
print("\n=== ui credit block ===")
print(" ", json.dumps(ui.get("credit"), indent=1)[:600])
print("  tavily totals:", json.dumps((ui.get("tavily") or {}).get("totals")))
print("  tavily usage:", json.dumps((ui.get("tavily") or {}).get("usage")))
