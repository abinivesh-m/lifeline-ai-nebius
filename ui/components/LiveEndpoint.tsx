"use client";

import { useEffect, useState } from "react";

type Health = {
  status?: string;
  engine?: {
    provider?: string;
    label?: string;
    tiers?: Record<string, string>;
    configured?: boolean;
    mode?: string;
  };
  modes?: string[];
};

type Allocate = {
  status?: string;
  detail?: string;
  mode?: string;
  source?: string;
  allocation?: { hospital?: number; water_pump?: number };
  total?: number;
  justification?: string;
  validation?: { ok?: boolean; problems?: string[] };
  brain?: {
    provider?: string;
    model?: string;
    status?: string;
    latency_s?: number;
    cost_usd?: number;
  };
};

type State =
  | { kind: "checking" }
  | { kind: "static"; detail: string }
  | { kind: "live"; health: Health }
  | { kind: "running"; health: Health }
  | { kind: "done"; health: Health; result: Allocate }
  | { kind: "error"; health: Health; detail: string };

export default function LiveEndpoint() {
  const [state, setState] = useState<State>({ kind: "checking" });

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    fetch("/api/health", { signal: controller.signal, cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<Health>;
      })
      .then((health) => {
        if (health?.status === "ok") setState({ kind: "live", health });
        else setState({ kind: "static", detail: "health route answered without an engine" });
      })
      .catch(() =>
        setState({
          kind: "static",
          detail: "no Python process on this host - the static build serves baked artefacts",
        })
      )
      .finally(() => clearTimeout(timer));
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, []);

  const run = async () => {
    if (state.kind !== "live" && state.kind !== "done" && state.kind !== "error") return;
    const health = state.health;
    setState({ kind: "running", health });
    try {
      const response = await fetch("/api/allocate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ mode: "auto" }),
      });
      const result = (await response.json()) as Allocate;
      if (result.status !== "ok") {
        setState({ kind: "error", health, detail: result.detail || `HTTP ${response.status}` });
        return;
      }
      setState({ kind: "done", health, result });
    } catch (error) {
      setState({ kind: "error", health, detail: String(error) });
    }
  };

  const health = "health" in state ? state.health : undefined;
  const live = state.kind === "live" || state.kind === "running" || state.kind === "done" || state.kind === "error";
  const result = state.kind === "done" ? state.result : undefined;
  const staticDetail = state.kind === "static" ? state.detail : "";

  return (
    <div className="mt-3 rounded-xl border border-line bg-[#08141a] p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="mono text-[10px] tracking-[0.18em] text-muted">05 · LIVE ENDPOINT</div>
        <span
          className={`rounded border px-1.5 py-0.5 mono text-[8.5px] tracking-[0.1em] ${
            state.kind === "checking"
              ? "border-line text-muted"
              : live
              ? "border-teal/50 bg-teal/10 text-teal"
              : "border-amber/50 bg-amber/10 text-amber"
          }`}
        >
          {state.kind === "checking"
            ? "CHECKING"
            : live
            ? `LIVE · ${health?.engine?.tiers?.decision?.split("/").pop() ?? "ENGINE"}`
            : "STATIC BUILD"}
        </span>
      </div>

      {live ? (
        <>
          <p className="mt-2 max-w-[95ch] text-[11.5px] leading-relaxed text-muted">
            This host runs the Python engine. One click calls Nemotron 3 Ultra on Nebius Token Factory,
            re-runs the validator in code, and returns a fresh allocation. It spends about half a cent;
            nothing is dispatched and the human gate still holds.
          </p>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <button
              onClick={run}
              disabled={state.kind === "running"}
              className="rounded-md border border-teal bg-teal/15 px-3 py-1.5 mono text-[10px] font-bold tracking-[0.08em] text-teal transition hover:bg-teal/25 disabled:opacity-50"
            >
              {state.kind === "running" ? "CALLING ULTRA…" : "RUN LIVE ALLOCATION →"}
            </button>
            <span className="mono text-[9px] text-muted">
              POST /api/allocate · mode=auto · {health?.engine?.provider ?? "Nebius Token Factory"}
            </span>
          </div>

          {state.kind === "error" && (
            <p className="mt-2 rounded border border-blood/40 bg-blood/10 px-2 py-1.5 mono text-[9.5px] text-blood">
              {state.detail}
            </p>
          )}

          {result && (
            <div className="mt-3 rounded-lg border border-line/70 bg-black/25 p-3">
              <div className="flex flex-wrap gap-5">
                <Metric label="HOSPITAL" value={`${result.allocation?.hospital ?? "—"} L`} colour="#f87171" />
                <Metric label="WATER PUMP" value={`${result.allocation?.water_pump ?? "—"} L`} colour="#60a5fa" />
                <Metric label="TOTAL" value={`${result.total ?? "—"} L`} colour="#2dd4bf" />
                <Metric
                  label="VALIDATOR"
                  value={result.validation?.ok ? "PASS" : "FAIL"}
                  colour={result.validation?.ok ? "#2dd4bf" : "#f87171"}
                />
              </div>
              <p className="mt-2 max-w-[100ch] text-[11px] leading-relaxed text-muted">
                {result.justification || "the validator accepted the proposal field by field"}
              </p>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 mono text-[9px] text-muted">
                <span>source · {result.source}</span>
                <span>model · {result.brain?.model?.split("/").pop() ?? "policy"}</span>
                <span>latency · {result.brain?.latency_s ?? "—"} s</span>
                <span>cost · ${Number(result.brain?.cost_usd ?? 0).toFixed(6)}</span>
                <span className="text-teal">nothing dispatched · human gate holds</span>
              </div>
            </div>
          )}
        </>
      ) : (
        <p className="mt-2 max-w-[100ch] text-[11.5px] leading-relaxed text-muted">
          {state.kind === "checking"
            ? "Checking whether this host runs the engine…"
            : staticDetail}
          {state.kind === "static" && (
            <>
              {" "}The recorded result is above; the same call runs with{" "}
              <span className="mono text-ink">python allocator.py --mode auto</span> or against the
              Nebius AI Cloud container.
            </>
          )}
        </p>
      )}
    </div>
  );
}

function Metric({ label, value, colour }: { label: string; value: string; colour: string }) {
  return (
    <div>
      <div className="mono text-[8.5px] tracking-[0.14em] text-muted">{label}</div>
      <div className="text-lg font-bold" style={{ color: colour }}>
        {value}
      </div>
    </div>
  );
}
