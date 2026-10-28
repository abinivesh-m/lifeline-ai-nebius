# Feedback — Nebius Token Factory, NVIDIA Nemotron 3, Tavily

Written from this build, 26–30 October 2026, by a solo entrant in India. Every point below is
something that happened while shipping, not a suggestion from a landing page.

## 1. Builder approval and credits: the wait is the product problem

The Builder Program approval and the $25 credit arrived in **two separate emails roughly two hours
apart**. During that window the console showed an active-looking project with a **$0 balance**, and
there was no way to tell "not approved yet" from "approved, credits failed". I re-checked the
dashboard four times and re-read the same page.

The cost was not two hours of waiting; it was **two hours of not knowing whether to start**. For a
hackathon with a fixed deadline, that uncertainty is worse than a queue with a number on it.

**Suggestion:** put approval state in the console as a live status (`pending review` → `approved` →
`credits applied`, with a timestamp), and let the credit land automatically on approval instead of a
second email. Even a "typically 2 h, you are #N" line would have removed the ambiguity.

## 2. Once approved, the path is genuinely fast

Key creation and the first successful call were the best part of the experience: **zero to
hello-world in about two minutes**, with the balance reading **$29.50** live on the dashboard. The
endpoint is OpenAI-compatible, so the switch was a `base_url` and a key — no SDK, no proxy, no GPU
instance. That is exactly the promise the track makes, and it held.

## 3. Docs cover the switch, not the wait

The docs are accurate on `base_url`, model listing and auth, which is what a migration needs. What
they do not cover is the state *before* approval, which is where a deadline-bound entrant actually
lives. A small "what you can and cannot do while pending" page would have saved the confusion in §1.

## 4. Model IDs need one alias table

`GET /v1/models` is the only trustworthy source, and it is good that it exists — but the catalogue
carries near-identical names (`nvidia/Nemotron-3-Super-VL`, `nvidia/Nemotron-3.5-Super`, and
`nvidia/nemotron-3-super-120b-a12b` all coexist). Choosing the right one for a tier took a manual
diff. One canonical table mapping **marketing name → model id → price → context → modality** would
remove a whole class of silent mistakes.

## 5. Cost is computable but not returned

The response gives token counts, not cost. I priced every call myself from the per-million rates
listed on the model catalogue, which works but means my ledger is only as correct as my copy of the
price table. A `usage.cost_usd` field, or a pricing endpoint keyed by model id, would make spend
auditable by the platform instead of by the customer.

## 6. Per-request latency is on you

Total latency for one JSON-mode Ultra completion was **2–3.4 s** across my runs (1.98 s on the first
probe, 3.37 s in the proof run), which is fine for
an allocation decision. I did not measure time-to-first-token because there is no streaming trace in
the response — for the voice path, TTFT is the number that matters, so a `first_token_ms` or
streaming timings would be the single most useful addition for voice apps.

## 7. Deploying a web app is possible but assumes Docker

Serverless Endpoints accept an arbitrary image and a container command, which is how this project's UI
is meant to ship. The docs, however, assume a locally built and pushed image. On a machine without
Docker, the only route is a registry build (CI) or cloning the repo from the container command. A
"deploy from a public repo" option, or a documented no-Docker path in the quickstart, would have
turned a two-hour detour into ten minutes.

## 8. Tavily: the honest scores are the feature

Tavily's relevance score and its `answer` field are what made a verifiable evidence layer possible:
when my query was wrong, the API said *"the sources don't provide a definitive answer"* instead of
inventing one, and the low scores (0.01–0.19) told me the result set was noise. That is rare and
useful.

Two small asks:

- **`published_date` is missing for several major outlets** (The Hindu, Times of India article pages).
  I had to recover dates from the URL path (`/2026/Oct/22/`) and from the byline in the body. A
  normalised `published_date` in `extract` results — not just in `search` — would remove that.
- **`extract` has no way to ask "did this page actually contain this sentence?"** I implemented
  literal-quote verification client-side. A `must_include` parameter on `extract` would let the
  platform enforce it server-side and return a clean pass/fail per URL.

Neither is a blocker. Both would have saved code.

## Summary

| Area | Rating | Why |
| --- | --- | --- |
| Token Factory once approved | 9/10 | two minutes to hello-world, OpenAI-compatible, no infra |
| Approval / credit visibility | 4/10 | two hours of not knowing, no live status |
| Model catalogue clarity | 6/10 | authoritative but ambiguous near-duplicate IDs |
| Cost transparency | 7/10 | token counts yes, cost no |
| Tavily for verifiable evidence | 9/10 | honest scores and answers; dates need normalising |
| Nebius deploy path without Docker | 5/10 | possible, under-documented |

Would I recommend Nemotron 3 on Token Factory? **Yes, with the caveat in §1.** The inference is
boring in the best way — it answered in a few seconds, returned valid JSON, and never needed a retry — and
the three-tier pricing is what let me put a 550B model behind a single decision instead of treating
it as a demo.
