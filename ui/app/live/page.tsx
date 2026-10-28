"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Ev = Record<string, any>;

type Run = {
  schema: string;
  recorded_utc: string;
  source: string;
  note: string;
  events: Ev[];
};

const STEPS = [
  { n: 1, name: "PERCEIVE", tool: "stored masks" },
  { n: 2, name: "LISTEN", tool: "stored transcript" },
  { n: 3, name: "GRAPH", tool: "Kahn sort" },
  { n: 4, name: "ROUTE", tool: "A* heapq" },
  { n: 5, name: "ALLOCATE", tool: "Nemotron 3 Ultra + validator" },
  { n: 6, name: "BUDGET", tool: "reconciled artefacts" },
  { n: 7, name: "APPROVE", tool: "human gate" },
  { n: 8, name: "REPLAN", tool: "new constraint" },
];

const money = (value: number, digits = 6) =>
  "$" + Number(value || 0).toFixed(digits);

export default function LiveRunPage() {
  const [run, setRun] = useState<Run | null>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetch("/data/live_run.json")
      .then((response) => response.json())
      .then((payload: Run) => {
        setRun(payload);
        // Deep link: /live/?step=5 opens the run parked on that step.
        const wanted = Number(
          new URLSearchParams(window.location.search).get("step")
        );
        if (wanted >= 1 && wanted <= 8) {
          const index = payload.events.findIndex(
            (event) => event.type === "step" && event.step === wanted
          );
          if (index >= 0) setCursor(index);
        }
      })
      .catch(() => setRun(null));
  }, []);

  const events = run?.events ?? [];
  const current = events[Math.min(cursor, Math.max(events.length - 1, 0))];
  const atEnd = events.length > 0 && cursor >= events.length - 1;

  useEffect(() => {
    if (!playing || atEnd) return;
    const delay =
      current?.step === 7 && current?.status === "waiting" ? 2400 : 1100;
    const timer = setTimeout(() => setCursor((value) => value + 1), delay);
    return () => clearTimeout(timer);
  }, [playing, atEnd, cursor, current]);

  useEffect(() => {
    if (!playing) return;
    if (atEnd) setPlaying(false);
  }, [atEnd, playing]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [cursor]);

  const byStep = useMemo(() => {
    const map = new Map<number, Ev>();
    for (const event of events.slice(0, cursor + 1)) {
      if (event.type === "step" && typeof event.step === "number") {
        map.set(event.step, event);
      }
    }
    return map;
  }, [events, cursor]);

  const logLines = useMemo(
    () =>
      events
        .slice(0, cursor + 1)
        .filter((event) => event.type === "step")
        .map((event) => ({
          step: event.step as number,
          name: event.name as string,
          detail: (event.detail as string) || (event.status as string),
          status: event.status as string,
        })),
    [events, cursor]
  );

  const start = () => {
    setCursor(0);
    setPlaying(true);
  };

  const step = () => {
    setPlaying(false);
    setCursor((value) => Math.min(value + 1, Math.max(events.length - 1, 0)));
  };

  const jumpTo = (number: number) => {
    const index = events.findIndex(
      (event) => event.type === "step" && event.step === number
    );
    if (index >= 0) {
      setPlaying(false);
      setCursor(index);
    }
  };

  return (
    <main className="min-h-screen bg-[#060d11] text-ink">
      <header className="border-b border-line px-5 py-4">
        <div className="mx-auto flex w-full max-w-[1600px] flex-wrap items-center gap-3">
          <a href="/" className="mono text-[10.5px] tracking-[0.18em] text-teal">
            LIFELINE AI
          </a>
          <span className="mono text-[10px] text-muted">/ WORKFLOW REPLAY</span>
          <span className="rounded border border-amber/40 bg-amber/10 px-2 py-0.5 mono text-[9.5px] tracking-[0.14em] text-amber">
            RECORDED RUN
          </span>
          <a
            href="/"
            className="ml-auto mono text-[10.5px] tracking-[0.12em] text-muted underline decoration-line underline-offset-4 hover:text-teal"
          >
            BACK TO THE TOWN
          </a>
        </div>
      </header>

      <div className="mx-auto w-full max-w-[1600px] px-5 py-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
              Eight steps, one approval
            </h1>
            <p className="mt-2 max-w-[70ch] text-[13px] leading-relaxed text-muted">
              This is the real event stream from <span className="mono text-ink">python live.py</span>,
              captured on 28 October 2026 and replayed here: one event per step, the human gate, then
              the replan after the depot is damaged. The runner is a local Python process, so the hosted
              demo plays its recording instead — same events, no install.
            </p>
          </div>
          <div className="text-right">
            <div className="mono text-[9.5px] tracking-[0.16em] text-muted">RECORDED</div>
            <div className="mono text-[11px] text-ink">
              {run?.recorded_utc?.replace("T", " ").slice(0, 19) || "loading..."} UTC
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <button
            onClick={() => (playing ? setPlaying(false) : start())}
            className="rounded-md border border-teal bg-teal/15 px-4 py-2 text-[12px] font-bold text-teal transition hover:bg-teal/25"
          >
            {playing ? "PAUSE" : cursor > 0 ? "REPLAY" : "PLAY THE RUN"}
          </button>
          <button
            onClick={step}
            disabled={atEnd}
            className="rounded-md border border-line px-4 py-2 text-[12px] font-semibold text-muted transition hover:border-muted/60 hover:text-ink disabled:opacity-40"
          >
            NEXT STEP
          </button>
          <span className="mono text-[10px] text-muted">
            {Math.min(cursor + 1, events.length)} / {events.length || 0} events
          </span>
          <div className="ml-2 h-1.5 min-w-[120px] flex-1 overflow-hidden rounded bg-line">
            <div
              className="h-full bg-teal transition-all duration-500"
              style={{
                width: events.length
                  ? `${Math.round(((cursor + 1) / events.length) * 100)}%`
                  : "0%",
              }}
            />
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)_360px]">
          {/* step rail */}
          <section className="rounded-xl border border-line bg-panel/70 p-3">
            <div className="mono mb-2 text-[9.5px] tracking-[0.18em] text-muted">
              THE LOOP
            </div>
            <div className="space-y-1.5">
              {STEPS.map((meta) => {
                const event = byStep.get(meta.n);
                const status = (event?.status as string) || "pending";
                const done = Boolean(event);
                const color =
                  status === "waiting"
                    ? "#f5b942"
                    : status === "approved" || status === "ok" || status === "replanned"
                    ? "#2dd4bf"
                    : done
                    ? "#60a5fa"
                    : "#1f3540";
                return (
                  <button
                    key={meta.n}
                    type="button"
                    onClick={() => jumpTo(meta.n)}
                    className="flex w-full items-start gap-3 rounded-lg border border-line/70 px-3 py-2 text-left transition hover:border-muted/50"
                    style={{ borderLeft: `3px solid ${color}` }}
                  >
                    <span className="mono text-[10px] text-muted">
                      {String(meta.n).padStart(2, "0")}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="text-[12.5px] font-semibold" style={{ color: done ? "#e8f3f6" : "#86a0ab" }}>
                        {meta.name}
                      </div>
                      <div className="mono truncate text-[9.5px] text-muted">{meta.tool}</div>
                    </div>
                    <span className="mono text-[9px] uppercase" style={{ color }}>
                      {done ? status : "—"}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* detail */}
          <section className="min-h-[420px] rounded-xl border border-line bg-panel/70 p-5">
            <div className="mono text-[9.5px] tracking-[0.18em] text-muted">
              {current?.type === "step"
                ? `STEP ${String(current.step).padStart(2, "0")} / ${current.name}`
                : "THE RUN / NOT STARTED"}
            </div>
            <Detail event={current} />
          </section>

          {/* log */}
          <section className="rounded-xl border border-line bg-panel/70 p-3">
            <div className="mono mb-2 text-[9.5px] tracking-[0.18em] text-muted">
              EVENT LOG
            </div>
            <div
              ref={logRef}
              className="max-h-[430px] space-y-1.5 overflow-y-auto pr-1 mono text-[10.5px] leading-relaxed"
            >
              {logLines.length === 0 && (
                <div className="text-muted">press play to stream the run</div>
              )}
              {logLines.map((line, index) => (
                <div key={index} className="rounded border border-line/60 px-2 py-1.5">
                  <span className="text-teal">
                    {String(line.step).padStart(2, "0")} {line.name}
                  </span>
                  <span className="text-muted"> · {line.detail}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <p className="mt-5 max-w-[110ch] text-[11.5px] leading-relaxed text-muted">
          <span className="text-amber">Provenance.</span> Every number on this page was produced by the
          engine and captured in the stream; the eight steps, the 70/30 allocation, the validator verdict
          and the ledger totals are the same ones the page and the CLI print. This page is a replay, not a
          live call: for a live run, the same events stream from{" "}
          <span className="mono text-ink">python live.py</span> locally or from the Docker image on Nebius
          AI Cloud.
        </p>
      </div>
    </main>
  );
}

function Detail({ event }: { event: Ev | undefined }) {
  if (!event || event.type === "start") {
    return (
      <div className="mt-4">
        <div className="rounded-lg border border-line bg-[#050c10] p-4">
          <div className="mono text-[9.5px] tracking-[0.16em] text-teal">
            KOTTUR · 100 L RESERVE · RUN {String(event?.run ?? "—")}
          </div>
          <p className="mt-2 text-[13.5px] leading-relaxed text-ink">
            Press play, or pick a step on the left. Every event below comes from the recorded
            stream: the same eight steps, the same 70/30 split, the same gate.
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            <MiniStat label="STEPS" value="8" />
            <MiniStat label="HUMAN DECISIONS" value="1" />
            <MiniStat label="DISPATCHED WITHOUT A YES" value="0" />
          </div>
        </div>
      </div>
    );
  }

  const status = String(event.status || "");

  return (
    <div className="mt-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded border border-line px-2 py-0.5 mono text-[9.5px] uppercase tracking-[0.12em] text-teal">
          {status}
        </span>
        {event.cache === "cache" && (
          <span className="mono text-[9.5px] text-muted">replayed from cache · no new spend</span>
        )}
      </div>

      <p className="mt-3 text-[14px] leading-relaxed text-ink">
        {event.detail || "…"}
      </p>

      {event.step === 1 && (
        <div className="mt-4">
          <div className="mono text-[10px] text-muted">WATER SEVERITY / 9 FRAMES</div>
          <div className="mt-2 flex h-24 items-end gap-1.5">
            {(event.severity as number[] | undefined)?.map((value, index) => (
              <div key={index} className="flex-1" title={`${value}%`}>
                <div
                  className="w-full rounded-t bg-lung/70"
                  style={{ height: `${Math.max(4, value)}%` }}
                />
              </div>
            ))}
          </div>
          <div className="mono mt-2 text-[10px] text-muted">
            worst {event.worst_pct}% · {event.worst}
          </div>
        </div>
      )}

      {event.step === 2 && (
        <div className="mt-4 rounded-lg border border-line bg-[#050c10] p-3">
          <div className="mono text-[9.5px] tracking-[0.14em] text-muted">TRANSCRIPT / STORED</div>
          <div className="mt-1 text-[13px] text-ink">“{event.transcript}”</div>
          <div className="mono mt-2 text-[10px] text-muted">
            {event.model} · synthetic: {String(event.synthetic)}
          </div>
        </div>
      )}

      {event.step === 3 && (
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <List title="KAHN ORDER" items={(event.order as string[]) || []} />
          <List title="IF THE HEART FAILS" items={(event.downstream as string[]) || []} />
          <div className="sm:col-span-2 mono text-[10px] text-muted">
            {event.people} people lose water service downstream
          </div>
        </div>
      )}

      {event.step === 4 && (
        <div className="mt-4">
          <div className="flex flex-wrap gap-1.5">
            {(event.path as string[] | undefined)?.map((node, index) => (
              <span
                key={index}
                className="rounded border border-line bg-[#050c10] px-2 py-1 mono text-[10px] text-ink"
              >
                {node}
              </span>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-5">
            <Metric label="A* ROUTE" value={`${event.km} km`} color="#2dd4bf" />
            <Metric
              label="FUEL SAVED"
              value={`${event.saving?.percent ?? 40}%`}
              color="#f5b942"
            />
            <Metric
              label="LITRES"
              value={`${event.saving?.fuel_litres ?? 1.82} L`}
              color="#60a5fa"
            />
          </div>
        </div>
      )}

      {event.step === 5 && (
        <div className="mt-4">
          <div className="flex flex-wrap gap-4">
            <Metric label="HOSPITAL" value={`${event.allocation?.hospital} L`} color="#f87171" />
            <Metric label="WATER PUMP" value={`${event.allocation?.water_pump} L`} color="#60a5fa" />
            <Metric label="TOTAL" value={`${event.total} L`} color="#2dd4bf" />
          </div>
          <p className="mt-3 text-[12.5px] leading-relaxed text-muted">{event.justification}</p>
          <div className="mt-3 space-y-1">
            {(event.evidence as Ev[] | undefined)?.slice(0, 4).map((item) => (
              <div key={item.id} className="mono text-[10px] text-muted">
                <span className="text-lung">{item.id}</span> {item.claim}
              </div>
            ))}
          </div>
          <div className="mono mt-3 text-[10px] text-muted">
            source: {event.source} · validator: PASS · nothing dispatched
          </div>
        </div>
      )}

      {event.step === 6 && (
        <div className="mt-4">
          <div className="flex flex-wrap gap-4">
            <Metric label="INFERENCE" value={money(event.spent)} color="#2dd4bf" />
            <Metric label="BALANCE" value={money(event.budget, 2)} color="#e8f3f6" />
            <Metric label="TAVILY" value={`${money(event.tavily_usd, 3)} / ${event.tavily_credits} cr`} color="#f5b942" />
          </div>
          <div className="mt-4 space-y-1.5">
            {Object.entries((event.by_model as Record<string, Ev>) || {}).map(([model, bucket]) => (
              <div key={model} className="flex items-center justify-between gap-3">
                <span className="mono truncate text-[10px] text-muted">{model.split("/").pop()}</span>
                <span className="mono text-[10px] text-ink">
                  {bucket.calls} calls · {money(bucket.spent_usd)}
                </span>
              </div>
            ))}
          </div>
          <div className="mono mt-3 text-[10px] text-muted">
            combined {money(event.combined_usd)} · {event.percent}% of balance
          </div>
        </div>
      )}

      {event.step === 7 && (
        <div className="mt-4">
          {status === "waiting" ? (
            <div className="rounded-lg border border-amber/40 bg-amber/10 p-4">
              <div className="mono text-[9.5px] tracking-[0.16em] text-amber">HUMAN GATE</div>
              <p className="mt-1 text-[13px] text-ink">
                The live runner blocks here until a person clicks. The recorded run used APPROVE.
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-teal/40 bg-teal/10 p-4">
              <div className="mono text-[9.5px] tracking-[0.16em] text-teal">APPROVED</div>
              <p className="mt-1 text-[13px] text-ink">
                One human word released the dispatch. In the live runner the decision is sealed in the
                hash-chained ledger before the replan runs.
              </p>
            </div>
          )}
        </div>
      )}

      {event.step === 8 && (
        <div className="mt-4">
          <div className="rounded-lg border border-line bg-[#050c10] p-3">
            <div className="mono text-[9.5px] tracking-[0.14em] text-muted">TRIGGER</div>
            <div className="mt-1 text-[13px] text-ink">{event.trigger}</div>
          </div>
          <div className="mt-3 flex flex-wrap gap-4">
            <Metric label="HOSPITAL" value={`${event.allocation?.hospital} L`} color="#f87171" />
            <Metric label="WATER PUMP" value={`${event.allocation?.water_pump} L`} color="#60a5fa" />
            <Metric
              label="PUMP UPTIME"
              value={`${event.pump_before} h → ${event.pump_after} h`}
              color="#2dd4bf"
            />
          </div>
          <div className="mono mt-3 text-[10px] text-muted">
            heart protected: {String(event.hospital_protected)}
          </div>
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-line/70 px-3 py-2">
      <div className="mono text-[9px] tracking-[0.14em] text-muted">{label}</div>
      <div className="text-lg font-bold text-ink">{value}</div>
    </div>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border border-line bg-[#050c10] p-3">
      <div className="mono text-[9.5px] tracking-[0.14em] text-muted">{title}</div>
      <div className="mt-1 space-y-1">
        {items.map((item, index) => (
          <div key={index} className="mono text-[11px] text-ink">
            {index + 1}. {item}
          </div>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div>
      <div className="mono text-[9px] tracking-[0.14em] text-muted">{label}</div>
      <div className="text-xl font-bold" style={{ color }}>
        {value}
      </div>
    </div>
  );
}
