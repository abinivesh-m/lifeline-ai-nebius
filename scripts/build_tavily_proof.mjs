// Builds ui/public/proof/tavily.html from the committed artefacts.
// Every number and every pass/fail flag on the page is read from disk here —
// nothing is typed by hand.
//
//   node scripts/build_tavily_proof.mjs
//
// Inputs:  artifacts/tavily_proof.json, ui/public/data/lifeline.json
// Output:  ui/public/proof/tavily.html

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const read = (p) => JSON.parse(readFileSync(join(root, p), "utf8"));

const proof = read("artifacts/tavily_proof.json");
const lifeline = read("ui/public/data/lifeline.json");

const credit = lifeline.credit;
const totals = lifeline.tavily.totals;
const live = proof.modes.live;
const scenario = proof.modes.scenario;

const host = (u) => {
  try {
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
};

// The 17 scored claims. Each one exists twice on disk: once in the site data
// (score, verdict) and once in the proof file (the five gate flags). Join them
// on the quote, which is unique per claim, and keep only rows that match.
const all = [...live.excerpts, ...scenario.excerpts];

const rows = lifeline.tavily.claims
  .map((c) => {
    const e = all.find((x) => x.quote === c.quote && x.claim === c.topic);
    if (!e) throw new Error(`no proof excerpt for ${c.topic} / ${c.url}`);
    if (Math.abs(e.relevance - c.score) > 1e-9) {
      throw new Error(`score drift on ${c.url}: ${e.relevance} vs ${c.score}`);
    }
    return {
      topic: c.topic,
      mode: c.mode,
      title: c.title,
      url: c.url,
      host: host(c.url),
      published: c.published,
      score: c.score,
      quote: e.quote,
      ql: e.quote_literal,
      uf: e.url_fetched,
      dc: e.date_check,
      ro: e.region_ok,
      accepted: c.accepted,
      verdict: c.verdict,
    };
  })
  .sort((a, b) => b.score - a.score);

const accepted = rows.filter((r) => r.accepted).length;

// The cached first-run example that never entered the totals.
const m25 = scenario.rejected_examples[0];

// Counts per gate, straight off the 17 rows.
const gateCount = (key) => rows.filter((r) => r[key]).length;
const gatePass = (key) => rows.filter((r) => r[key] === true).length;

// A date passes when the artefact says it landed inside the window ("fresh"
// for the live search, "in-window" for the cached scenario run).
const dateOk = (r) => r.dc === "fresh" || r.dc === "in-window";

const stats = {
  checked: totals.claims_checked,
  accepted: totals.claims_accepted,
  queries: totals.queries,
  fetched: totals.urls_fetched,
  failed: totals.urls_failed,
  credits: credit.tavily_credits,
  calls: credit.tavily_calls,
  usd: credit.tavily_usd,
};

const data = JSON.stringify(rows).replace(/</g, "\\u003c");

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>17 claims, 5 gates | Lifeline AI</title>
<style>
  :root {
    --ink:#e8f3f6; --muted:#7d97a3; --panel:#0c191f; --panel2:#0a151a;
    --line:#1e3641; --teal:#2dd4bf; --blood:#f87171; --amber:#f5b942; --bg:#050d11;
  }
  *{box-sizing:border-box}
  html,body{margin:0;background:var(--bg);color:var(--ink)}
  body{
    font-family:"Segoe UI",system-ui,sans-serif;height:100vh;overflow:hidden;
    background-image:
      radial-gradient(1100px 600px at 8% -12%,rgba(45,212,191,.11),transparent 62%),
      radial-gradient(800px 520px at 100% 0%,rgba(245,185,66,.07),transparent 60%),
      linear-gradient(rgba(30,54,65,.28) 1px,transparent 1px),
      linear-gradient(90deg,rgba(30,54,65,.28) 1px,transparent 1px);
    background-size:auto,auto,64px 64px,64px 64px;
  }
  .mono{font-family:"Cascadia Mono",Consolas,monospace}
  .wrap{max-width:1800px;margin:0 auto;padding:34px 60px 26px;height:100vh;display:flex;flex-direction:column}

  header{display:flex;align-items:center;gap:16px;padding-bottom:14px;border-bottom:1px solid var(--line)}
  .brand{font-weight:700;letter-spacing:.22em;font-size:14px}
  .brand span{color:var(--muted);font-weight:400}
  .tag{font-size:10.5px;letter-spacing:.2em;color:var(--amber);border:1px solid rgba(245,185,66,.3);
       border-radius:999px;padding:5px 12px}
  .tally{margin-left:auto;display:flex;gap:26px;align-items:baseline}
  .tally div{font-size:10px;letter-spacing:.16em;color:var(--muted);text-transform:uppercase}
  .tally b{display:block;font-family:"Cascadia Mono",Consolas,monospace;font-size:19px;
           letter-spacing:-.01em;color:var(--ink);font-weight:600;margin-top:2px}
  .tally b.t{color:var(--teal)} .tally b.r{color:var(--blood)}

  .head{display:flex;align-items:flex-end;gap:28px;margin:22px 0 18px}
  h1{font-size:40px;line-height:1.06;letter-spacing:-.025em;margin:0;font-weight:700}
  h1 em{font-style:normal;color:var(--teal)}
  .sub{font-size:15px;line-height:1.5;color:var(--muted);max-width:620px;margin:0 0 4px}
  .sub b{color:var(--ink);font-weight:600}
  .run{margin-left:auto;display:flex;align-items:center;gap:12px}
  .run button{
    font-family:"Cascadia Mono",Consolas,monospace;font-size:12px;letter-spacing:.14em;
    color:#04211d;background:var(--teal);border:0;border-radius:7px;padding:12px 20px;
    cursor:pointer;transition:transform .15s,box-shadow .15s,opacity .15s;font-weight:700}
  .run button:hover{transform:translateY(-1px);box-shadow:0 6px 22px rgba(45,212,191,.28)}
  .run button:disabled{opacity:.45;cursor:default;transform:none;box-shadow:none}
  .hint{font-size:11px;color:var(--muted);letter-spacing:.08em}

  .gates{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:18px}
  .gate{border:1px solid var(--line);border-radius:9px;background:var(--panel);
        padding:11px 14px;position:relative;overflow:hidden;transition:border-color .2s}
  .gate.on{border-color:rgba(45,212,191,.45)}
  .gate .n{font-family:"Cascadia Mono",Consolas,monospace;font-size:10px;color:var(--amber);
           letter-spacing:.14em}
  .gate .k{font-family:"Cascadia Mono",Consolas,monospace;font-size:12.5px;margin-top:3px}
  .gate .c{position:absolute;right:13px;top:11px;font-family:"Cascadia Mono",Consolas,monospace;
           font-size:11px;color:var(--muted)}
  .gate .c b{color:var(--ink);font-weight:600}

  .main{display:grid;grid-template-columns:1fr 470px;gap:26px;flex:1;min-height:0}

  .grid{display:grid;grid-template-columns:repeat(6,1fr);grid-auto-rows:1fr;gap:11px;min-height:0}
  .tile{
    position:relative;border:1px solid var(--line);border-radius:9px;background:var(--panel2);
    padding:14px 15px;cursor:pointer;text-align:left;color:inherit;font:inherit;
    display:flex;flex-direction:column;overflow:hidden;
    transition:transform .16s,border-color .16s,background .16s;
    opacity:0;transform:translateY(10px);animation:rise .5s cubic-bezier(.2,.8,.2,1) forwards;
  }
  @keyframes rise{to{opacity:1;transform:none}}
  body.static .tile{animation:none;opacity:1;transform:none}
  .tile:hover{transform:translateY(-2px);border-color:rgba(232,243,246,.35);background:#0e1e25}
  .tile.sel{border-color:var(--teal);background:#0f2429;box-shadow:0 0 0 1px rgba(45,212,191,.4) inset}
  .tile.no.sel{border-color:var(--blood);background:#20141a;box-shadow:0 0 0 1px rgba(248,113,113,.4) inset}
  .tile .s{font-family:"Cascadia Mono",Consolas,monospace;font-size:25px;font-weight:600;
           letter-spacing:-.03em;line-height:1}
  .tile.ok .s{color:var(--teal)} .tile.no .s{color:var(--blood)}
  .tile .k{font-size:11px;letter-spacing:.1em;color:var(--muted);text-transform:uppercase;margin-top:12px}
  .tile .h{font-family:"Cascadia Mono",Consolas,monospace;font-size:9.5px;color:#5d7681;
           margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .tile .dots{display:flex;gap:3px;margin-top:auto;padding-top:12px}
  .tile .dots i{width:100%;height:3px;border-radius:2px;background:rgba(45,212,191,.75)}
  .tile .dots i.f{background:rgba(248,113,113,.9)}
  .tile .m{position:absolute;right:11px;top:11px;font-size:13px;line-height:1}
  .tile.ok .m{color:var(--teal)} .tile.no .m{color:var(--blood)}
  .tile .bar{position:absolute;left:0;bottom:0;height:2px;background:currentColor;opacity:.55;
             width:var(--w);transition:width .5s ease}
  .tile.ok .bar{color:var(--teal)} .tile.no .bar{color:var(--blood)}
  .tile.flash{animation:flash .42s ease}
  @keyframes flash{0%{background:#17323a}100%{background:var(--panel2)}}
  .tile.ok.flash{background:#123028}
  .tile.no.flash{background:#2a161c}

  .detail{border:1px solid var(--line);border-radius:12px;background:linear-gradient(180deg,#0d1b22,#08141a);
          padding:24px 26px;display:flex;flex-direction:column;min-height:0;position:relative;overflow:hidden}
  .detail:before{content:"";position:absolute;left:0;top:0;height:2px;width:100%;
                 background:linear-gradient(90deg,var(--teal),transparent)}
  .detail.no:before{background:linear-gradient(90deg,var(--blood),transparent)}
  .dhead{display:flex;align-items:center;gap:10px;margin-bottom:14px}
  .dhead .idx{font-family:"Cascadia Mono",Consolas,monospace;font-size:11px;color:var(--muted);
              letter-spacing:.14em}
  .dhead .mode{margin-left:auto;font-family:"Cascadia Mono",Consolas,monospace;font-size:10px;
               color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:3px 7px}
  .dtitle{font-size:19px;line-height:1.35;font-weight:600;margin:0 0 6px}
  .dsrc{font-family:"Cascadia Mono",Consolas,monospace;font-size:11px;color:var(--muted);margin-bottom:14px}
  .dq{font-size:13px;line-height:1.62;color:#a8c0ca;font-style:italic;border-left:2px solid var(--line);
      padding-left:12px;margin:0 0 16px;max-height:132px;overflow:hidden}
  .checks{display:flex;flex-direction:column;gap:1px;margin-bottom:16px}
  .chk{display:flex;align-items:center;gap:10px;font-family:"Cascadia Mono",Consolas,monospace;
       font-size:12px;padding:7px 0;border-bottom:1px solid rgba(30,54,65,.5)}
  .chk .i{width:14px;text-align:center;font-size:11px}
  .chk .n{color:var(--muted);width:118px}
  .chk .v{margin-left:auto;color:var(--ink);font-size:11.5px}
  .chk.pass .i{color:var(--teal)} .chk.fail .i{color:var(--blood)}
  .chk.fail .n{color:var(--blood)} .chk.fail .v{color:var(--blood)}
  .verdict{margin-top:auto;display:flex;align-items:center;gap:12px}
  .verdict .pill{font-family:"Cascadia Mono",Consolas,monospace;font-size:12px;letter-spacing:.06em;
                 padding:8px 13px;border-radius:6px;font-weight:600}
  .verdict .pill.ok{color:var(--teal);background:rgba(45,212,191,.1);border:1px solid rgba(45,212,191,.35)}
  .verdict .pill.no{color:var(--blood);background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.35)}
  .verdict .note{font-size:11.5px;color:var(--muted);line-height:1.45}

  footer{display:flex;align-items:center;gap:12px;margin-top:16px;padding-top:12px;
         border-top:1px solid var(--line);font-family:"Cascadia Mono",Consolas,monospace;
         font-size:10.5px;color:var(--muted);letter-spacing:.04em}
  footer .x{color:var(--blood)}
  footer .sep{color:#314a55}
  footer .r{margin-left:auto}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="brand">LIFELINE AI <span>/ PROOF</span></div>
    <div class="tag">TAVILY · EVIDENCE LAYER</div>
    <div class="tally">
      <div>checked<b class="mono" id="t-checked">0</b></div>
      <div>accepted<b class="mono t" id="t-accepted">0</b></div>
      <div>rejected<b class="mono r" id="t-rejected">0</b></div>
      <div>credits<b class="mono">${stats.credits}</b></div>
      <div>spend<b class="mono">$${stats.usd.toFixed(3)}</b></div>
    </div>
  </header>

  <div class="head">
    <div>
      <h1>Every fact has to pass <em>five checks</em>.</h1>
      <p class="sub">Tavily returns candidates. <b>Code</b> decides which ones become facts —
      a literal quote from a fetched page, inside the window, above the floor, from the right region.</p>
    </div>
    <div class="run">
      <span class="hint">click a claim · or</span>
      <button id="run">RUN THE GATE</button>
    </div>
  </div>

  <div class="gates">
    <div class="gate" data-gate="0"><div class="n">01</div><div class="k">quote_literal</div>
      <div class="c"><b>${gatePass("ql")}</b>/${rows.length}</div></div>
    <div class="gate" data-gate="1"><div class="n">02</div><div class="k">url_fetched</div>
      <div class="c"><b>${gatePass("uf")}</b>/${rows.length}</div></div>
    <div class="gate" data-gate="2"><div class="n">03</div><div class="k">date_check</div>
      <div class="c"><b>${rows.filter(dateOk).length}</b>/${rows.length}</div></div>
    <div class="gate" data-gate="3"><div class="n">04</div><div class="k">relevance &ge; 0.20</div>
      <div class="c"><b>${rows.filter((r) => r.score >= 0.2).length}</b>/${rows.length}</div></div>
    <div class="gate" data-gate="4"><div class="n">05</div><div class="k">region_ok</div>
      <div class="c"><b>${gatePass("ro")}</b>/${rows.length}</div></div>
  </div>

  <div class="main">
    <div class="grid" id="grid"></div>
    <div class="detail" id="detail">
      <div class="dhead"><span class="idx" id="d-idx">CLAIM 01 / ${rows.length}</span>
        <span class="mode" id="d-mode"></span></div>
      <h2 class="dtitle" id="d-title"></h2>
      <div class="dsrc" id="d-src"></div>
      <p class="dq" id="d-quote"></p>
      <div class="checks" id="d-checks"></div>
      <div class="verdict">
        <span class="pill ok" id="d-pill">accepted</span>
        <span class="note" id="d-note"></span>
      </div>
    </div>
  </div>

  <footer>
    <span class="x">✕</span>
    <span>kept outside the totals — cached first run: ${m25.title.replace(/\s*-\s*BBC\.com$/, "")},
      relevance ${m25.relevance.toFixed(4)} &lt; 0.20, regional check also fails</span>
    <span class="sep">|</span>
    <span>${stats.queries} queries · ${stats.fetched} pages · ${stats.failed} failures · ${stats.calls} calls</span>
    <span class="r">artifacts/tavily_proof.json</span>
  </footer>

</div>

<script>
const DATA = ${data};
const rows = DATA;
const qs = new URLSearchParams(location.search);
const STATIC = qs.get("static") === "1";
if (STATIC) document.body.classList.add("static");
const grid = document.getElementById("grid");
const detail = document.getElementById("detail");
let selected = 0;

const CHECK_NAMES = ["quote_literal","url_fetched","date_check","relevance ≥ 0.20","region_ok"];

function checksFor(r) {
  return [
    { pass: r.ql === true, value: r.ql === true ? "slice of page" : "not literal" },
    { pass: r.uf === true, value: r.uf === true ? r.host : "not fetched" },
    { pass: r.dc === "fresh" || r.dc === "in-window", value: r.dc },
    { pass: r.score >= 0.2, value: r.score.toFixed(3) + (r.score >= 0.2 ? " ≥ 0.20" : " < 0.20") },
    { pass: r.ro === true, value: r.ro === true ? "in region" : "not in region" },
  ];
}

function tile(r, i) {
  const b = document.createElement("button");
  b.className = "tile " + (r.accepted ? "ok" : "no");
  b.dataset.i = i;
  b.style.animationDelay = (i * 34) + "ms";
  b.style.setProperty("--w", Math.max(4, Math.round(r.score * 100)) + "%");
  const dots = checksFor(r).map((c) =>
    '<i class="' + (c.pass ? "p" : "f") + '"></i>').join("");
  b.innerHTML =
    '<span class="m">' + (r.accepted ? "✓" : "✕") + '</span>' +
    '<span class="s">' + r.score.toFixed(3) + '</span>' +
    '<span class="k">' + r.topic.replace(/_/g, " ") + '</span>' +
    '<span class="h">' + r.host + '</span>' +
    '<span class="dots">' + dots + '</span>' +
    '<span class="bar"></span>';
  b.addEventListener("click", () => select(i));
  b.addEventListener("mouseenter", () => select(i, true));
  return b;
}

function select(i, preview) {
  selected = i;
  const r = rows[i];
  document.querySelectorAll(".tile").forEach((el) =>
    el.classList.toggle("sel", Number(el.dataset.i) === i));

  detail.className = "detail " + (r.accepted ? "" : "no");
  document.getElementById("d-idx").textContent =
    "CLAIM " + String(i + 1).padStart(2, "0") + " / " + rows.length;
  document.getElementById("d-mode").textContent = r.mode;
  document.getElementById("d-title").textContent = r.title.replace(/\\s*\\|\\s*.*$/, "");
  document.getElementById("d-src").textContent = r.host + " · " + r.published;

  let q = r.quote.replace(/^\\[\\.\\.\\.\\]\\s*/, "");
  const chrome = q.match(/^.*?\\bCopied\\s+/);
  if (chrome) q = q.slice(chrome[0].length);
  document.getElementById("d-quote").textContent = q.length > 300 ? q.slice(0, 300) + "…" : q;

  const checks = checksFor(r);
  document.getElementById("d-checks").innerHTML = checks.map((c, k) =>
    '<div class="chk ' + (c.pass ? "pass" : "fail") + '">' +
      '<span class="i">' + (c.pass ? "✓" : "✕") + '</span>' +
      '<span class="n">' + CHECK_NAMES[k] + '</span>' +
      '<span class="v">' + c.value + '</span>' +
    '</div>').join("");

  const pill = document.getElementById("d-pill");
  pill.className = "pill " + (r.accepted ? "ok" : "no");
  pill.textContent = r.accepted ? "ACCEPTED" : "REJECTED";
  document.getElementById("d-note").textContent =
    r.accepted ? "all five gates passed" : r.verdict.replace(/^rejected:\\s*/, "");
}

rows.forEach((r, i) => grid.appendChild(tile(r, i)));

// Counters.
function count(el, to, ms) {
  const t0 = performance.now();
  (function step(t) {
    const p = Math.min(1, (t - t0) / ms);
    el.textContent = Math.round(to * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}
if (STATIC) {
  document.getElementById("t-checked").textContent = rows.length;
  document.getElementById("t-accepted").textContent = rows.filter((r) => r.accepted).length;
  document.getElementById("t-rejected").textContent = rows.filter((r) => !r.accepted).length;
} else {
  count(document.getElementById("t-checked"), rows.length, 700);
  count(document.getElementById("t-accepted"), rows.filter((r) => r.accepted).length, 900);
  count(document.getElementById("t-rejected"), rows.filter((r) => !r.accepted).length, 1100);
}

// RUN THE GATE — sweeps the tiles left to right, one verdict at a time.
const runBtn = document.getElementById("run");
runBtn.addEventListener("click", () => {
  runBtn.disabled = true;
  const tiles = [...document.querySelectorAll(".tile")];
  tiles.forEach((el, i) => setTimeout(() => {
    el.classList.add("flash");
    setTimeout(() => el.classList.remove("flash"), 460);
    if (i === tiles.length - 1) {
      setTimeout(() => { runBtn.disabled = false; }, 700);
    }
  }, i * 105));
});

// Arrow keys walk the grid; Enter is not needed because hover already previews.
window.addEventListener("keydown", (e) => {
  if (e.key === "ArrowRight" || e.key === "ArrowDown") select(Math.min(rows.length - 1, selected + 1));
  if (e.key === "ArrowLeft" || e.key === "ArrowUp") select(Math.max(0, selected - 1));
});

// Deep links for testing: ?claim=3 selects a row, ?run=1 fires the sweep.
select(Math.min(rows.length - 1, Number(qs.get("claim") || 0)));
if (qs.get("run") === "1") setTimeout(() => runBtn.click(), 400);
</script>
</body>
</html>
`;

writeFileSync(join(root, "ui/public/proof/tavily.html"), html, "utf8");
console.log(
  `wrote ui/public/proof/tavily.html — ${rows.length} claims, ${accepted} accepted`
);
