# Devpost submission pack — copy/paste

**Track:** Best Apps and Agents · **Bonus:** Best Use of Tavily · **Feedback:** yes

> **Before pasting:** every number below is read from a committed artefact. The demo URL below was
> verified 200 in a private window on 28 Oct 2026 — re-check it the morning you submit. Do not name an
> event that is not linked. Do not quote a source count the artefact does not contain. No API key or
> account id belongs in any field.

## Form fields at a glance

| Devpost field | What to paste |
| --- | --- |
| Project name | `Lifeline AI` |
| Elevator pitch | the 140-character line below |
| Video | public YouTube URL, **≤ 3:00**, and the audio must say *Nebius Token Factory*, *NVIDIA Nemotron 3* and *Tavily* |
| Thumbnail | `figma/lifegrid.png` |
| GitHub repo | `https://github.com/abinivesh-m/lifeline-ai-nebius` |
| Demo URL | `https://lifeline-ai-nebius.vercel.app` — static demo, verified 200 anonymously 28 Oct 2026 |
| Feedback | paste [`FEEDBACK.md`](../FEEDBACK.md) — eight findings from this build |

---

## Project name

```
Lifeline AI
```

## Elevator pitch (150 char limit)

```
When roads die, Lifeline AI rations the last 100 L of diesel — offline, deterministic, evidence-checked with Tavily, reasoned by Nemotron 3.
```

(140 characters.)

---

## About the project

```markdown
## The problem is ordering, not supply

A landslide takes the only road. The fuel depot is on the far side, the hospital generator has four
hours left, and the water pump runs off the hospital's feeder. There are 100 litres in town.

Split them 50/50 and the feeder browns out: the pump burns fuel it cannot use and stops after 30
minutes. Give the hospital its 70 litres first and the same pump runs 90 minutes on its 30. Same
diesel, same town, three times the water — because the constraint is dependency order, not quantity.

**Lifeline AI is the agent that computes that order when the cloud, the road and the phone network are
all gone.**

## What it does

```
100 L diesel  ->  hospital 70 L + pump 30 L      exactly 100, no waste
route         ->  7.8 km village road vs 13.0 km signposted bypass   (-40% trip fuel)
pump uptime   ->  30 min -> 90 min               water back in 2 h instead of 6 h
decision      ->  held at a human gate, never auto-executed
```

Eight steps: perceive, listen, graph, route, allocate, budget, approve, replan. **Four of them — graph,
route, budget, replan — need no model and no network.** That is deliberate: if the road is down, the
cloud may be down too, and a survival tool that stops working in an outage is a demo.

## Why it is an agent, not a wrapper

Three separations, each enforced by tests:

1. **The model proposes, code disposes.** Nemotron returns `{"allocation", "justification"}`. Every
   field goes through the same validator the deterministic solver uses. Over-allocation, a short
   total, or starving the heart while funding the lungs is rejected with a reason and the policy
   solver takes over. The 70/30 result ships either way.
2. **Evidence and inference are separate objects.** Each evidence item carries the exact
   `town.json` path it came from; each inference cites evidence ids. A test resolves every path and
   every cited id, so an invented justification fails CI.
3. **Web facts are quoted, not summarised.** See below.

## Nemotron 3 on Nebius Token Factory

Model IDs and prices are read from the live `GET /v1/models` response, not typed from memory:

| Tier | Model | $/M in → out | Role |
| --- | --- | --- | --- |
| fast | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 0.06 → 0.24 | one measured triage call; too slow for long drafts |
| deep | `nvidia/nemotron-3-super-120b-a12b` | 0.30 → 0.90 | 8-locale drafting **and** review of every locale |
| decision | `nvidia/Nemotron-3-Ultra-550b-a55b` | 1.00 → 3.00 | the one allocation that matters |

**Measured on the allocation path:** one live Ultra call, `temperature=0`, JSON mode — **3.37 s**,
valid JSON, `{"hospital": 70, "water_pump": 30}`, validator **PASS**. Reproduce with
`python scripts/nebius_single_call.py`.

The tiering is the architecture, not a badge: Super absorbs the drafting and review volume so Ultra
is affordable for the single decision where reasoning changes the outcome. The same 8-language
prompt took 59 s and returned empty content on Nano at a 6,000-token cap, 38 s on Nano at 16,000,
and **6.7 s on Super at 6,000** — that measurement is why drafting runs on Super. One file
(`brain.py`) knows a provider exists; the engine exports no model name.

**What it cost, and why.** Every priced call is in the artefacts: **18 Nebius inference calls for
$0.027049** — Ultra once at $0.004968, Super 16 times at $0.021929, Nano once at $0.000152 — and
**132 Tavily credits for $1.056** across 47 calls, **$1.083049** combined against the $29.50 balance.
Inference used 0.0917% of it. The deterministic core — Kahn, A*, the 70/30 solver, the validator, the
ledger, the gate — makes no network call and costs $0.00. That split is deliberate: reasoning is cheap
and rare; proof is expensive and frequent, because a rejected claim still costs credits and a verifier
that accepts everything would save a dollar and destroy the product.

## Tavily: the outside world has to be checkable

The town's own numbers come from `town.json`. Everything outside it — what a landslide does to a
highway, what a generator needs — comes from the web, and a judge must be able to check it without
trusting me.

Four endpoints do real work at `advanced` depth: **search** (ranked results + answer + raw content +
image descriptions, domain- and date-bounded), **extract** (the pages actually opened, 20 per batch,
per-URL failures reported), **map** (site structure of the cited authority), **crawl** (map + extract
in one hop).

A claim is accepted only when five checks pass (four gates plus the conditional date rule):

1. the quote is a **literal slice** of the fetched body (`quote in text` is true by construction);
2. the URL appears in an **extract success** list — a search hit is a lead, not a source;
3. an **event** claim carries a date inside the window (2023 for the scenario replay, 45 days for
   live); a **mechanism** claim ("generators run on diesel") may be timeless — it is labelled as such;
4. Tavily's own relevance score clears **0.20**;
5. the source is **regional to the town** (configurable: `LIFELINE_REGION_TERMS`).

The first run failed check 4 because it did not exist: a BBC story about an **M25 footbridge** was
accepted as "landslide closes road" purely on the word *closed*, at score **0.01**. That row is still
in `artifacts/tavily_proof.json`, rejected, next to the rows that passed. The artefact shows the false
positive the verifier caught — that is the point of publishing it.

Scenario and live are stored and rendered separately, never blended, because blending is how a 2023
figure gets quoted as current. Every response is cached by request hash, so the artefact rebuilds
offline and replaying it costs zero credits; credits are read from the API's own `usage` field.

## Honesty about the scenario

The town is real — Kottur, Pollachi Taluk, at the foot of the Western Ghats, where the
**Pollachi–Valparai ghat road** closes under boulders every monsoon. The most recent real closure was
**22 October 2026, reopened after 15 hours**. The 6-hour closure, the 100 L reserve and the 70/30 split
are **simulated town data**, calibrated to that recurring event. I do not claim a specific landslide
happened on a specific date.

The same pattern exists on every continent: one road, one fuel reserve, one hospital–pump–shelter
chain. Nothing in the code knows the word "Kottur" — the organ graph, road network and demands are
data, so pointing it at another town is a JSON file and a region string.

## Deterministic core

- A* over 9 surveyed edges with a haversine heuristic, audited for admissibility, cross-checked
  against brute-force enumeration of every simple path.
- Kahn topological sort with cycle detection and a measured cascade blast radius.
- Seeded ant colony (12 × 12, seed 7): the blocked trail falls below 1% after 8 iterations.
- 70/30 constrained solver + validator; the 50/50 counterfactual is computed, not narrated.
- **78 acceptance tests**, standard library only.

## What we learned

A model that returns perfectly good JSON can still be *wrong about the world*, and no prompt fixes
that. The verifier does. The second lesson is cheaper: measure one real call before building a
pipeline around a model name - a valid 70/30 at 3.37 s changed the design more than any benchmark
table.
```

---

## Built with (max 25 tags)

```
nebius, token factory, nvidia, nemotron, nemotron-3-ultra, nemotron-3-super, nemotron-3-nano,
tavily, tavily-search, tavily-extract, python, next.js, react, three.js, typescript, tailwindcss,
a-star, topological-sort, ant-colony, offline-first, multilingual, mms-tts, json-mode, mit-license
```

---

## Try it out

| Field | Value |
| --- | --- |
| GitHub | `https://github.com/abinivesh-m/lifeline-ai-nebius` |
| Demo | `https://lifeline-ai-nebius.vercel.app` |

The demo is the full interface with every artefact baked in, served as a static export. `POST /api/allocate`
is the one route that needs the Python engine, so it answers in the included Nebius container
(`deploy/serve.py`) and not on the static host. I list only the URL I watched return 200 in a private
window; there is no Nebius-hosted URL in this submission because I have not deployed there.

---

## Additional info → "Is your project new or existing?"

```markdown
Existing. An earlier prototype (August 2026) proved the deterministic core — Kahn order, A* 7.8 km vs
the 13.0 km bypass, 70/30 allocation, 78 tests, offline run on a 6 GB laptop — but it called a single
hosted model through a different provider and had no way to verify any fact that came from outside its
own data file.

What changed during the submission period:

1. **Provider seam (`brain.py`).** All inference now goes through Nebius Token Factory's
   OpenAI-compatible endpoint. Three tiers resolve from the live catalogue: Nano for volume, Super for
   review, Ultra for the allocation decision. Prices are read from the same response, so the spend
   ledger is not based on a hand-copied table.
2. **Ultra on the decision path.** The allocation is now reasoned by Nemotron 3 Ultra with the town
   constraints and retrieved evidence in context; measured at 3.37 s, valid JSON, validator PASS.
3. **A new evidence subsystem (`evidence.py`).** Tavily search/extract/map/crawl, a request-hash cache
   for free replay, and a five-check verifier that rejects a source when the quote is not literal, the
   page was not fetched, the date is outside the window, the relevance score is too low, or the source
   is outside the town's region. This did not exist before.
4. **Two never-blended evidence modes** (scenario replay vs live web), rendered and stored separately.
5. **Rebrand and cleanup.** Every reference to the previous provider was removed from code, UI and
   artefacts; the licence is unmodified MIT so GitHub detects it. Stored masks and transcripts are
   labelled by role, not by the old vendor.
6. **Deployment work** on Nebius AI Cloud Serverless Endpoints (container command + env secret, no key
   in the repo).

The original prototype repository is untouched; this is a separate public repository.
```

---

## "Which model(s) did you use, and why that size/variant?"

```markdown
Three sizes of Nemotron 3, because the workload has three different shapes.

nvidia/Nemotron-3-Ultra-550b-a55b (decision) — one call per allocation, where the answer is a
constrained allocation plus a justification that a human will read before releasing diesel. It needs
the town constraints, the dependency order and the retrieved evidence in one context, and it needs to
reason about trade-offs. Latency is acceptable because it happens once: measured 3.37 s for a
JSON-mode completion.

nvidia/nemotron-3-super-120b-a12b (deep) — review. Every localised payload is re-read for invented
numbers, clinical content, wrong language and false dispatch claims before it can ship. This is a
higher-volume, lower-stakes-per-call job, so the mid tier fits.

nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B (fast) — triage. A small MoE is the cheap first pass; on this
task it was measured too slow for long drafts (59 s and empty content at a 6,000-token cap), so the
volume work moved to Super.

The point of using three is the same reason the app exists: spend the expensive model on the decision,
not on the formatting.
```

## "Rate Nemotron's output quality (1–10)"

```markdown
8. On the allocation path the first Ultra call returned valid JSON with no retry, the correct 70/30
split under the hard constraints, a justification that referenced the actual evidence, and it passed
the validator - at 3.37 s. That is a strong result for a zero-shot, no-fine-tune prompt.

I am not scoring it 10 because I have not finished measuring it: multilingual quality across Tamil,
Swahili and Arabic, and JSON validity across many repeated calls, are still being validated. A single
excellent call is evidence, not a distribution.
```

## "Fine-tune, prompt-engineer, or out of the box?"

```markdown
Out of the box, prompt-engineered, no fine-tuning.

Three prompts for three tiers. All of them share a hard system constraint: fuel allocation only, no
medical advice, and the output schema is fixed (`allocation`, `justification`, `confidence`). The
decision prompt carries the town's dependency order, the hard constraints (reserve, per-organ demand,
feeder dependency) and the verified evidence rows with their source ids. Temperature is 0 and JSON
mode is on; the client also retries once without `response_format` if a gateway rejects the field,
so a formatting incompatibility cannot lose the call.

Because the validator is provider-independent, the prompt only has to produce a *candidate*. A model
that ignores the constraints produces a rejection, not a bad allocation.
```

## "How did Nemotron compare to other models you've used?"

```markdown
Direct comparison is limited to what I measured on this task, which is one dimension: a constrained
JSON allocation.

The previous prototype's model also produced a valid 70/30 allocation, so on the headline answer they
agree. The difference is in the trace: Ultra's justification referenced the retrieved evidence and the
feeder dependency, and it did so in one call at 3.37 s with no retry. Earlier local attempts on a 6 GB
laptop GPU needed regex cleanup around the JSON and were slower per useful answer.

I am deliberately not publishing a benchmark table across providers from single runs. Two calls is not
a benchmark, and a fabricated comparison is worse than none.
```

## "Which Nebius capabilities were most valuable?"

```markdown
Token Factory's OpenAI-compatible endpoint, by a wide margin. The migration was a base_url, a key and
a model id — no SDK, no proxy, no GPU instance — and `GET /v1/models` is the authoritative source for
both ids and prices, which is what let me price calls from real token counts instead of a table I
typed. Switching Ultra → Super → Nano is one line in `brain.py`, which is the entire reason the app
can afford a 550B model on the decision and a small one everywhere else.

Serverless AI is where the full demo is meant to run: an endpoint with a container command and an
environment secret, so the deployed app calls Token Factory from inside Nebius with no key in the
repository. The URL in this submission is the static demo I watched return 200 in a private window; the
`/api/allocate` route runs in that container, not on the static host. I do not list a Nebius-hosted URL
because I have not deployed there.

What I did not need: a GPU instance. The agent side runs on a 6 GB laptop, offline, which is the
point.
```

## "Likely to recommend Nemotron on Nebius (1–10)"

```markdown
9. Once approved, it was the fastest path from a key to a working inference call I have used: about two
minutes to hello-world, an OpenAI-compatible surface, and three price tiers that make a large model
usable for a single important call. I withhold the tenth point for the approval experience — the credit
arrived in a separate email and the dashboard showed $0 with no status, which is two hours of not
knowing whether to start. Full detail in the written feedback.
```

## "Experience vs previous cloud/local (1–10)"

```markdown
8. Better than the local-GPU path on this task: no model download, no VRAM ceiling, no OOM, and a
stable latency for a JSON completion. It is also less work than wiring a second hosted provider,
because the API shape is the one every OpenAI-compatible client already speaks. The two points come off
for the pre-approval ambiguity and for cost not being returned in the response — I compute it from
token counts, which works but is my arithmetic, not the platform's.
```

## "What would have made the experience better?"

```markdown
1. Live approval state in the console (`pending` → `approved` → `credits applied`) with automatic
   credit application on approval. The two-hour wait was survivable; the dashboard showing $0 with no
   status was not.
2. A canonical alias table: marketing name → model id → price → context → modality. The catalogue
   currently carries `nvidia/Nemotron-3-Super-VL`, `nvidia/Nemotron-3.5-Super` and
   `nvidia/nemotron-3-super-120b-a12b`, and picking the right tier took a manual diff.
3. `usage.cost_usd` in the response, or a pricing endpoint keyed by model id, so spend is auditable by
   the platform rather than by the customer.
4. Streaming timings (time-to-first-token) — total latency is enough for an allocation, but for the
   voice path TTFT is the number that decides whether it feels alive.
5. A documented no-Docker deploy path for Serverless Endpoints (deploy from a public repo, or a
   quickstart that does not assume a local image build). That detour cost more time than the
   integration did.
```

## "What do you hope to see from the Nemotron team next?"

```markdown
A small, quantised Nemotron that runs on a 6 GB consumer GPU without a cloud round-trip, because the
whole premise here is that the network may be gone. And streaming-first multilingual output: the
approval gate is spoken, so first-token latency and native Tamil/Swahili prosody matter more than
another benchmark point on English reasoning.
```

## "Did you use Tavily?" → **Yes**

```markdown
Functional runtime calls, four endpoints, at advanced depth: POST /search (answer, raw content, image
descriptions, domain and date filters), POST /extract (20 URLs per batch, per-URL failure reporting),
POST /map, POST /crawl. Claims are accepted only when the quote is a literal slice of the fetched body,
the URL was actually fetched, the date is inside the mode's window (event claims only), Tavily's
relevance score clears 0.20, and the source is regional to the town.

Everything is in `artifacts/tavily_proof.json`: per-row quote, URL, score, publication date, verdict,
plus the credits the API itself reported and the request ids. The merged run holds **10 queries, 65
leads, 37 fetched URLs (3 failures), 45 images, 10 answers, 2 maps, 3 crawls, 17 claims checked and
9 accepted**; the build consumed **132 credits across 47 calls**. Rebuild it offline with
`python evidence.py --combine` — responses are cached by request hash, so replay costs zero credits.
```

## "Which AI tools have you leveraged?"

```markdown
Nebius Token Factory for every inference call (Nemotron 3 Ultra 550b-a55b, Super 120b-a12b, Nano
30B-A3B). Tavily for all external evidence, with a verifier that can reject it. MMS-TTS, running
locally on CPU, for the spoken approval and alert clips — explicitly not an NVIDIA model, and labelled
as such on screen. Stored segmentation masks, captured before this build, for the flood-extent step;
Nebius Token Factory is text-only, so no image model is called or billed. Next.js, React and Three.js
for the interface.
```

---

## 60-second judge script (if they only watch the first minute)

> "This is a town that has lost its road. There are 100 litres of diesel and two things that need it:
> a hospital with four hours left, and a water pump that runs off the hospital's own feeder. Split it
> evenly and the pump dies in thirty minutes. [click RUN] Ultra on Token Factory returns 70/30 in 3.37
> seconds, the validator accepts it, and the pump now runs ninety. Every outside fact on this screen
> came from Tavily, and the sources it refused are shown next to the ones it accepted. Now the cable
> comes out — and the same plan still computes."
