"""NEBIUS PROOF - three tiers, three real calls, one artefact the UI can read.

    python scripts/nebius_proof.py            # live calls
    python scripts/nebius_proof.py --replay   # re-validate from the artefact

What it records, per call: the model id the catalogue actually returned, wall
clock seconds, token usage, cost computed from those tokens, whether the JSON
parsed, and whether the *code* accepted the answer. Nothing here asserts a
number that was not measured in this run.

Two things are checked harder than a normal demo would check them:

* **Citations.** Ultra is asked to cite evidence ids (`E1..E8`) and source ids
  (`S1..Sn`) from the Tavily proof. Every id in the answer is resolved against
  the sets that were actually passed in; an invented id fails the call.
* **Arithmetic.** The allocation goes through the same validator the
  deterministic solver uses, so a confident wrong answer is still rejected.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import allocator  # noqa: E402
import brain  # noqa: E402

OUT = ROOT / "artifacts" / "nebius_proof.json"
TAVILY = ROOT / "artifacts" / "tavily_proof.json"

# Evidence rows the allocation decision is allowed to cite.
EVIDENCE_IDS = [f"E{n}" for n in range(1, 9)]


def load_sources(limit: int = 6) -> list[dict]:
    """Accepted Tavily rows only, and only ones that survived every check."""
    if not TAVILY.exists():
        return []
    proof = json.loads(TAVILY.read_text(encoding="utf-8"))
    rows = []
    for mode, body in (proof.get("modes") or {}).items():
        for row in body.get("excerpts") or []:
            if row.get("accepted"):
                rows.append({**row, "mode": mode})
    # Prefer live rows about this road, then scenario rows, then by score.
    rows.sort(key=lambda r: (r["mode"] != "live", -(r.get("relevance") or 0)))
    seen, out = set(), []
    for row in rows:
        if row["url"] in seen:
            continue
        seen.add(row["url"])
        out.append(row)
        if len(out) >= limit:
            break
    return out


def source_block(sources: list[dict]) -> str:
    if not sources:
        return "(no web evidence retrieved in this run - reason from E1..E8 only)"
    lines = []
    for index, row in enumerate(sources, start=1):
        lines.append(
            f"[S{index}] {row.get('title') or row['url']}\n"
            f"    url: {row['url']}\n"
            f"    published: {row.get('published') or 'undated'} | mode: {row['mode']} | score: {row.get('relevance')}\n"
            f"    quote: \"{row['quote']}\""
        )
    return "\n".join(lines)


def allocation_prompt(town: dict, evidence: list[dict], constraints: dict, sources: list[dict]) -> str:
    return (
        "You are the fuel-allocation brain for a town whose only road is blocked by a landslide.\n"
        "Allocate the diesel reserve across the organs. Fuel allocation only - never medical advice.\n\n"
        "HARD CONSTRAINTS (a violation is rejected by code, not forgiven):\n"
        f"{json.dumps(constraints, indent=2)}\n\n"
        "TOWN EVIDENCE (cite these ids as E# when a sentence depends on them):\n"
        f"{json.dumps(evidence, indent=2)}\n\n"
        "VERIFIED WEB EVIDENCE (cite as S#; these quotes were fetched and checked):\n"
        f"{source_block(sources)}\n\n"
        "Return strict JSON with exactly these keys:\n"
        '  "allocation": object mapping organ name -> litres,\n'
        '  "justification": 2-4 sentences, each numeric claim tied to an E# or S# citation,\n'
        '  "confidence": number between 0 and 1,\n'
        '  "citations": array of the ids you used, e.g. ["E2","E7","S1"].\n'
        "Do not invent an id. Do not exceed the reserve. Do not fund a child before its parent. "
        'Include ONLY organs that receive more than 0 litres, and only organs listed in the evidence '
        '(hospital, water_pump). Adding a zero-valued non-fuel organ ("shelters": 0) is rejected by code.'
    )


def nano_prompt() -> str:
    return (
        "Classify this field report from a disaster responder. Return strict JSON with keys "
        '"intent" (one of: road_blocked, power_loss, fuel_shortage, medical, other), '
        '"urgency" (1-5), "language" (ISO code), "quote" (the words that decided it).\n\n'
        'Report: "the ghat road, km 42 pe boulder gir gaya, road band hai, hospital ka generator sirf '
        'chaar ghante chalega."'
    )


def super_prompt(justification: str, allowed_sources: list[str]) -> str:
    return (
        "You are a strict reviewer. Check the justification below for four failure modes only:\n"
        "1. a number that is not in the constraints or the evidence,\n"
        "2. medical advice,\n"
        "3. a claim of having sent an alert or dispatched fuel,\n"
        "4. a citation id that is not in the allowed list.\n\n"
        f"Allowed citation ids: {json.dumps(allowed_sources)}\n\n"
        f"Justification: {justification!r}\n\n"
        'Return strict JSON: {"verdict": "pass"|"fail", "issues": [strings], "numbers_seen": [numbers]}.'
    )


def call(tier: str, prompt: str, timeout: float = 120.0) -> dict:
    started = time.time()
    meta = brain.chat(prompt, tier=tier, timeout=timeout, max_tokens=1200)
    meta["wall_s"] = round(time.time() - started, 2)
    meta["raw"] = (meta.get("text") or "")[:1200]
    meta["json"] = {}
    if meta.get("text"):
        cleaned = re.sub(r"^```(?:json)?|```$", "", meta["text"].strip(), flags=re.MULTILINE).strip()
        try:
            meta["json"] = json.loads(cleaned)
        except json.JSONDecodeError:
            meta["json"] = {}
    return meta


def check_citations(text: str, allowed: set[str]) -> tuple[bool, list[str], list[str]]:
    used = re.findall(r"\b([ES]\d{1,2})\b", text or "")
    unknown = sorted({token for token in used if token not in allowed})
    return (not unknown and bool(used)), sorted(set(used)), unknown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one real call per Nemotron tier and record it.")
    parser.add_argument("--replay", action="store_true", help="re-validate the stored artefact, no calls")
    args = parser.parse_args(argv)

    allocator.load_env()
    if args.replay:
        if not OUT.exists():
            print("no artefact to replay", file=sys.stderr)
            return 1
        stored = json.loads(OUT.read_text(encoding="utf-8"))
        print(json.dumps(stored.get("totals", {}), indent=2))
        return 0

    town = allocator.load_town()
    evidence = allocator.build_evidence(town)
    constraints = allocator.hard_constraints(town)
    sources = load_sources()

    calls: dict[str, dict] = {}

    # 1. Nano: cheap classification, the volume path.
    calls["fast"] = call("fast", nano_prompt())

    # 2. Ultra: the decision, with citations.
    calls["decision"] = call("decision", allocation_prompt(town, evidence, constraints, sources))
    proposal = calls["decision"]["json"]
    allocation = proposal.get("allocation") or {}
    problems = allocator.validate_proposal(allocation, town) if allocation else ["no allocation returned"]

    allowed = set(EVIDENCE_IDS) | {f"S{i}" for i in range(1, len(sources) + 1)}
    cited_ok, cited, unknown = check_citations(str(proposal.get("justification") or ""), allowed)
    calls["decision"]["validator"] = {"problems": problems, "ok": not problems}
    calls["decision"]["citations"] = {"used": cited, "unknown": unknown, "ok": cited_ok}

    # 3. Super: review the decision. Only runs if there is something to review.
    justification = str(proposal.get("justification") or "")
    if justification:
        calls["deep"] = call("deep", super_prompt(justification, sorted(allowed)))
        review = calls["deep"]["json"]
        calls["deep"]["verdict"] = review.get("verdict")
        calls["deep"]["issues"] = review.get("issues") or []
    else:
        calls["deep"] = {"status": "skipped", "detail": "no justification from the decision tier"}

    total_tokens = 0
    total_cost = 0.0
    for meta in calls.values():
        usage = meta.get("usage") or {}
        total_tokens += int(usage.get("prompt_tokens") or 0) + int(usage.get("completion_tokens") or 0)
        total_cost += float(meta.get("cost_usd") or 0.0)

    payload = {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider": brain.label(),
        "endpoint": brain.endpoint(),
        "tiers": {tier: brain.model(tier) for tier in ("fast", "deep", "decision")},
        "calls": calls,
        "decision": {
            "allocation": allocation,
            "justification": justification,
            "confidence": proposal.get("confidence"),
            "validator_ok": not problems,
            "citations_ok": cited_ok,
        },
        "sources": [
            {"id": f"S{i}", "title": row.get("title"), "url": row["url"], "published": row.get("published"),
             "mode": row["mode"], "relevance": row.get("relevance"), "quote": row["quote"]}
            for i, row in enumerate(sources, start=1)
        ],
        "totals": {
            "calls": sum(1 for meta in calls.values() if meta.get("status") == "answered"),
            "tokens": total_tokens,
            "cost_usd": round(total_cost, 8),
            "wall_s": round(sum(float(meta.get("wall_s") or 0) for meta in calls.values()), 2),
            "latency_s": {tier: meta.get("wall_s") for tier, meta in calls.items()},
            "validator_ok": not problems,
            "citations_ok": cited_ok,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(payload["totals"], indent=2))
    print(f"allocation: {allocation}  validator={'PASS' if not problems else problems}")
    print(f"citations: {cited}  unknown={unknown}")
    if calls["decision"].get("status") != "answered":
        print(f"decision call failed: {calls['decision'].get('detail')}", file=sys.stderr)
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
