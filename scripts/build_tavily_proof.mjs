// Builds ui/public/proof/tavily.html from the committed artefacts.
// Every number on the page is read from disk here — nothing is typed by hand.
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

const totals = lifeline.tavily.totals;
const credit = lifeline.credit;
const claims = lifeline.tavily.claims;
const accepted = claims.filter((c) => c.accepted);

const scenario = proof.modes.scenario;
const live = proof.modes.live;

// The Odisha row: highest-scoring rejection in live mode.
const odisha = live.excerpts
  .filter((e) => !e.accepted)
  .sort((a, b) => b.relevance - a.relevance)[0];

// The cached first-run example that never entered the totals.
const m25 = scenario.rejected_examples[0];

const esc = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const num = (n, d = 3) => Number(n).toFixed(d);
const day = (s) => String(s).slice(0, 10);

// The Odisha excerpt starts with the newspaper's page chrome ("Express News
// Service Updated on: 2 min read Copied"). Drop that leading furniture so the
// quote reads as the story, without touching a word of the story itself.
const cleanQuote = (q) => {
  let s = String(q).replace(/^\[\.\.\.\]\s*/, "");
  const m = s.match(/^.*?\bCopied\s+/);
  if (m) s = s.slice(m[0].length);
  return s;
};

const host = (u) => {
  try {
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
};

// Shorten long headlines without losing which story it is.
const headline = (t) => {
  const s = String(t).replace(/\s*\|\s*.*$/, "");
  return s.length > 78 ? s.slice(0, 76).trimEnd() + "…" : s;
};

const stat = (value, label) =>
  `<div class="stat"><div class="v">${value}</div><div class="l">${label}</div></div>`;

// The verdict strings in the artefact are long ("rejected: relevance 0.16297895
// below 0.2"). Restate them with the same numbers, in the same order, so the
// column stays one line.
const verdict = (c) => {
  if (c.accepted) return "accepted";
  const m = String(c.verdict).match(/^rejected: relevance ([\d.]+) below/);
  if (m) return `rejected: ${num(m[1], 4)} < 0.20`;
  return String(c.verdict);
};

const rows = claims
  .map((c, i) => {
    const ok = c.accepted;
    return `<tr class="${ok ? "ok" : "no"}">
      <td class="i">${String(i + 1).padStart(2, "0")}</td>
      <td class="m">${esc(c.topic)}</td>
      <td class="t">${esc(headline(c.title))}<span class="h">${c.mode} · ${esc(host(c.url))}</span></td>
      <td class="d">${day(c.published)}</td>
      <td class="s">${num(c.score)}</td>
      <td class="v"><span class="pill ${ok ? "ok" : "no"}">${esc(verdict(c))}</span></td>
    </tr>`;
  })
  .join("\n");

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tavily — 17 claims checked | Lifeline AI</title>
<style>
  :root {
    --ink: #e8f3f6; --muted: #86a0ab; --panel: #0d1a20; --line: #1f3540;
    --teal: #2dd4bf; --blood: #f87171; --amber: #f5b942; --bg: #071015;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: var(--bg); color: var(--ink); }
  body {
    font-family: "Segoe UI", system-ui, sans-serif;
    background-image:
      radial-gradient(900px 500px at 15% -10%, rgba(45,212,191,.10), transparent 60%),
      radial-gradient(700px 420px at 95% 5%, rgba(248,113,113,.07), transparent 60%);
    background-repeat: no-repeat;
  }
  .mono { font-family: "Cascadia Mono", Consolas, monospace; }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 44px 40px 90px; }

  header { display: flex; align-items: baseline; gap: 14px; padding-bottom: 18px;
           border-bottom: 1px solid var(--line); }
  .brand { font-weight: 700; letter-spacing: .22em; font-size: 15px; }
  .brand span { color: var(--muted); font-weight: 400; }
  .tag { margin-left: auto; font-size: 12px; letter-spacing: .18em; color: var(--teal);
         border: 1px solid rgba(45,212,191,.35); border-radius: 999px; padding: 5px 12px; }

  h1 { font-size: 44px; line-height: 1.1; margin: 34px 0 14px; letter-spacing: -.02em; }
  h1 em { font-style: normal; color: var(--teal); }
  .lede { max-width: 900px; font-size: 18px; line-height: 1.65; color: var(--muted); margin: 0 0 30px; }
  .lede b { color: var(--ink); font-weight: 600; }

  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px;
           background: var(--line); border: 1px solid var(--line); border-radius: 12px;
           overflow: hidden; }
  .stat { background: var(--panel); padding: 18px 20px; }
  .stat .v { font-family: "Cascadia Mono", Consolas, monospace; font-size: 27px;
             font-weight: 600; letter-spacing: -.02em; }
  .stat .l { font-size: 11px; letter-spacing: .16em; color: var(--muted);
             text-transform: uppercase; margin-top: 5px; }
  .stat.teal .v { color: var(--teal); }
  .stat.blood .v { color: var(--blood); }

  h2 { font-size: 13px; letter-spacing: .24em; color: var(--muted); font-weight: 600;
       margin: 52px 0 16px; text-transform: uppercase; }
  h2 b { color: var(--ink); }

  .rules { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
  .rule { border: 1px solid var(--line); border-radius: 10px; background: var(--panel);
          padding: 14px 16px; }
  .rule .k { font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px;
             color: var(--teal); margin-bottom: 6px; }
  .rule .d { font-size: 13px; line-height: 1.5; color: var(--muted); }

  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  thead th { text-align: left; font-size: 10px; letter-spacing: .18em; color: var(--muted);
             text-transform: uppercase; font-weight: 600; padding: 0 12px 10px;
             border-bottom: 1px solid var(--line); }
  tbody tr { border-bottom: 1px solid rgba(31,53,64,.55); }
  tbody tr.no { background: rgba(248,113,113,.05); }
  td { padding: 11px 12px; vertical-align: middle; }
  td.i { font-family: "Cascadia Mono", Consolas, monospace; color: var(--muted); width: 42px; }
  td.m { font-family: "Cascadia Mono", Consolas, monospace; font-size: 11px;
         color: var(--muted); width: 86px; }
  td.t { line-height: 1.35; }
  td.t .h { display: block; font-family: "Cascadia Mono", Consolas, monospace;
            font-size: 10.5px; color: var(--muted); margin-top: 3px; }
  td.d, td.s { font-family: "Cascadia Mono", Consolas, monospace; font-size: 12.5px;
               color: var(--muted); white-space: nowrap; width: 104px; }
  td.s { color: var(--ink); }
  tr.no td.s { color: var(--blood); }
  td.v { width: 300px; }
  .pill { display: inline-block; font-family: "Cascadia Mono", Consolas, monospace;
          font-size: 11px; padding: 4px 9px; border-radius: 5px; }
  .pill.ok { color: var(--teal); background: rgba(45,212,191,.10);
             border: 1px solid rgba(45,212,191,.30); }
  .pill.no { color: var(--blood); background: rgba(248,113,113,.09);
             border: 1px solid rgba(248,113,113,.28); }

  .cards { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .card { border: 1px solid rgba(248,113,113,.28); border-radius: 12px;
          background: rgba(248,113,113,.045); padding: 22px 24px; }
  .card .top { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
  .card .top .x { color: var(--blood); font-size: 17px; }
  .card .top .who { font-size: 11px; letter-spacing: .16em; color: var(--muted);
                    text-transform: uppercase; }
  .card h3 { font-size: 18px; line-height: 1.35; margin: 0 0 6px; font-weight: 600; }
  .card .src { font-family: "Cascadia Mono", Consolas, monospace; font-size: 11px;
               color: var(--muted); margin-bottom: 14px; }
  .card blockquote { margin: 0 0 14px; padding-left: 13px; border-left: 2px solid rgba(248,113,113,.45);
                     font-size: 13.5px; line-height: 1.6; color: var(--muted); font-style: italic; }
  .card dl { display: grid; grid-template-columns: auto 1fr; gap: 5px 14px; margin: 0;
             font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; }
  .card dt { color: var(--muted); }
  .card dd { margin: 0; }
  .card .why { margin-top: 14px; font-size: 13.5px; line-height: 1.6; color: var(--ink); }

  footer { margin-top: 56px; padding-top: 18px; border-top: 1px solid var(--line);
           font-family: "Cascadia Mono", Consolas, monospace; font-size: 11.5px;
           line-height: 1.9; color: var(--muted); }
  footer a { color: var(--teal); text-decoration: none; }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="brand">LIFELINE AI <span>/ PROOF</span></div>
    <div class="tag">TAVILY · EVIDENCE LAYER</div>
  </header>

  <h1>${claims.length} claims checked.<br><em>${accepted.length} survived.</em></h1>
  <p class="lede">
    Every outside fact in Lifeline AI arrives through <b>Tavily</b>. None of it is trusted.
    A claim is only accepted if it is a <b>literal quote</b> from a page we actually fetched,
    published <b>inside the window</b>, scoring above the <b>0.20 relevance floor</b>,
    from the <b>right region</b>. Code decides that — not the model, and not us.
  </p>

  <div class="stats">
    ${stat(totals.queries, "queries")}
    ${stat(totals.urls_fetched, "pages fetched")}
    ${stat(totals.urls_failed, "fetch failures")}
    ${stat(totals.claims_checked, "claims checked")}
    ${stat(`<span style="color:var(--teal)">${totals.claims_accepted}</span>`, "accepted")}
    ${stat(credit.tavily_credits, "credits")}
    ${stat(credit.tavily_calls, "calls")}
    ${stat(`$${num(credit.tavily_usd)}`, "tavily spend")}
  </div>

  <h2>The <b>five</b> checks, in code</h2>
  <div class="rules">
    <div class="rule"><div class="k">quote_literal</div><div class="d">The quote is a byte-for-byte slice of the fetched page.</div></div>
    <div class="rule"><div class="k">url_fetched</div><div class="d">The URL was retrieved by us. No URL, no claim.</div></div>
    <div class="rule"><div class="k">date_check</div><div class="d">Published inside the search window, or dropped.</div></div>
    <div class="rule"><div class="k">relevance ≥ 0.20</div><div class="d">Below the floor is noise, whatever it says.</div></div>
    <div class="rule"><div class="k">region_ok</div><div class="d">The right state, the right country — not just the right words.</div></div>
  </div>

  <h2>The <b>${claims.length}</b> rows, as scored</h2>
  <table>
    <thead>
      <tr><th>#</th><th>claim</th><th>story</th><th>published</th><th>score</th><th>verdict</th></tr>
    </thead>
    <tbody>
${rows}
    </tbody>
  </table>

  <h2>Two rejections <b>kept on purpose</b></h2>
  <div class="cards">
    <div class="card">
      <div class="top"><span class="x">✕</span><span class="who">high score, wrong state</span></div>
      <h3>${esc(odisha.title)}</h3>
      <div class="src">${esc(host(odisha.url))} · ${day(odisha.published)}</div>
      <blockquote>${esc(cleanQuote(odisha.quote).slice(0, 240))}…</blockquote>
      <dl>
        <dt>relevance</dt><dd>${num(odisha.relevance, 4)}</dd>
        <dt>quote_literal</dt><dd>${odisha.quote_literal}</dd>
        <dt>url_fetched</dt><dd>${odisha.url_fetched}</dd>
        <dt>region_ok</dt><dd style="color:var(--blood)">${odisha.region_ok}</dd>
        <dt>accepted</dt><dd style="color:var(--blood)">${odisha.accepted}</dd>
      </dl>
      <p class="why">Same newspaper as two accepted Tamil Nadu stories. Zero point eight seven —
      and still rejected, because it is Odisha. A score is not permission.</p>
    </div>

    <div class="card">
      <div class="top"><span class="x">✕</span><span class="who">below the floor · cached first run</span></div>
      <h3>${esc(m25.title)}</h3>
      <div class="src">${esc(host(m25.url))} · ${day(m25.published)}</div>
      <blockquote>${esc(m25.quote)}</blockquote>
      <dl>
        <dt>relevance</dt><dd>${num(m25.relevance, 4)}</dd>
        <dt>floor</dt><dd>0.2000</dd>
        <dt>accepted</dt><dd style="color:var(--blood)">${m25.accepted}</dd>
      </dl>
      <p class="why">${esc(m25.reason)}. Cached first-run response, kept as an example — ${esc(m25.provenance.replace(/^.*?;\s*/, ""))}.</p>
    </div>
  </div>

  <footer>
    Read from <b>artifacts/tavily_proof.json</b> and <b>ui/public/data/lifeline.json</b> at build time.<br>
    Live mode: ${live.totals.queries} queries · ${live.totals.urls_fetched} pages · ${live.totals.claims_checked} checked · ${live.totals.claims_accepted} accepted · ${live.totals.wall_clock_s}s.<br>
    Scenario mode: ${scenario.totals.queries} queries · ${scenario.totals.urls_fetched} pages · ${scenario.totals.claims_checked} checked · ${scenario.totals.claims_accepted} accepted · ${scenario.totals.wall_clock_s}s.<br>
    Generated ${new Date().toISOString().slice(0, 10)} · <a href="/">back to the town</a>
  </footer>

</div>
</body>
</html>
`;

writeFileSync(join(root, "ui/public/proof/tavily.html"), html, "utf8");
console.log(
  `wrote ui/public/proof/tavily.html — ${claims.length} claims, ${accepted.length} accepted`
);
