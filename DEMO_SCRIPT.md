# Demo video script — 2:55, one take

Judges see the video, the repo and the UI. Nothing else. Every number below is read off the screen or
out of a committed artefact, and every claim is one the page can prove.

**Three phrases must be audible.** Say them once in a test recording and listen back:

1. **Nebius Token Factory**
2. **NVIDIA Nemotron 3**
3. **Tavily**

They appear at 0:56 and 1:18. Do not paraphrase them into "Nebius", "Nemotron" or "the search API".

---

## Before recording

```powershell
powershell -ExecutionPolicy Bypass -File scripts\refresh_demo.ps1
```

- The badge reads the reconciled artefacts, not the local ledger: deleting `credit_usage.json` does **not**
  change it. The page and the CLI report the same measured total.
- Do **not** run `python scripts/nebius_proof.py` after the badge is on screen: it appends a priced run and
  changes the call count.
- Do **not** re-run `python seri_gate.py` before filming: it appends fresh approvals and changes the
  ledger seq shown on screen.
- Close Chrome tabs, YouTube and Slack. The offline clip must show a quiet machine.
- Browser at 1920x1080, 100% zoom. Two tabs: the site, and `https://lifeline-ai-nebius.vercel.app/live/`.
- Open `artifacts/tavily_proof.json` in an editor at `modes.scenario.rejected_examples`.
- Record the audio on the same take. A voice-over added later drifts from the screen.

---

## 0:00 — the decision (8 s)

Section 01. Scroll slowly.

> "Kottur, Tamil Nadu. The road to the hospital is blocked at kilometre 42. Four hours of diesel left,
> two hundred people in the shelters, one hundred litres. One decision."

## 0:08 — the body (12 s)

Point at **BLOOD → HEART → LUNGS → ORGANS**.

> "Fuel is blood. If the heart stops, the lungs follow. That is a dependency graph, not a metaphor —
> and the agent sorts it before it spends a litre."

## 0:20 — the route (12 s)

Section 02.

> "The direct road is 4.2 kilometres and impassable. A* finds the 7.8 kilometre village road. Against the
> 13 kilometre bypass a human would actually drive, that is 40% less diesel."

## 0:32 — the eight steps (24 s)

Switch to the **`/live/`** tab. Press **PLAY THE RUN**. Let steps 1–5 land, pause at step 7 `waiting`,
then click through the approval.

> "This is the real event stream from the runner: eight steps, one human gate. Perceive, listen, order,
> route, allocate, budget, approve, replan. The model proposes at step five. Nothing moves until a person
> says yes."

Let step 8 finish on screen: the replan after the depot is damaged.

## 0:56 — the brain (22 s)

Section 06, then the proof artefact.

> "Reasoning runs on **NVIDIA Nemotron 3** on **Nebius Token Factory**, in three tiers. Nano for triage,
> Super for drafting and review, Ultra for the one decision that matters. We measured the choice: Nano
> burned six thousand tokens and returned nothing; Super answered the same prompt in 966 tokens and
> 6.7 seconds. Ultra returned 70 and 30 in 3.37 seconds, and the validator passed it."

## 1:18 — the evidence (30 s)

Section 04, then the JSON on screen.

> "Every outside fact comes from **Tavily**, and none of it is trusted. Accepted only if the quote is a
> literal slice of the fetched page, the URL was extracted, the date is inside the window, Tavily's
> relevance clears 0.20, and the source is regional. This New Indian Express story from 26 October scores
> 0.872 — and is rejected, because it is from Odisha. Same paper, wrong region."

Cut to the M25 row.

> "And this is the failure that created the rule: a BBC story about an M25 footbridge, score 0.014,
> accepted for a Kottur claim because both sentences said 'closed'. Both rows sit in the artefact,
> rejected, beside the nine that passed. Ten queries, 37 pages, 17 claims checked, 8 rejected, 132
> credits."

## 1:48 — the gate (22 s)

Section 05. Click two language chips, then play one clip.

> "The approval is not a button. A stored transcript is replayed, classified by Nemotron 3 Super, then
> checked in code: token, model, 80% confidence, or it is a no. A misheard no must never dispatch fuel.
> Seven languages are gated and sealed in a hash chain; Mandarin ships text-only because no voice
> checkpoint exists."

## 2:10 — offline (14 s)

Section 06, the prepared clip: airplane mode, `nvidia-smi`, `LIFELINE_OFFLINE=1 python agent.py --yes`.

> "Graph, route, validator, ledger, gate — all of it runs with the network off. The model is the fast
> path, not the only path."

## 2:24 — the bill (14 s)

> "Two point seven cents of inference across eighteen calls, and one dollar six on Tavily across a hundred
> and thirty-two credits, against a twenty-nine dollar fifty balance. The ledger prints every row."

## 2:38 — honesty and close (17 s)

Section 01 again, then the footer.

> "The town is real; the scenario is simulated, and the page says which is which. The masks and the
> transcript are stored artefacts, labelled. No message is claimed as sent. That is the product: a
> decision that survives the wire going down, and a town that can still say yes."

---

## What NOT to say

- Do not say the model runs on the laptop. Nemotron 3 runs on Nebius Token Factory; MMS-TTS is the local
  model.
- Do not say a message was sent. Every payload is `PENDING_CREDENTIALS`.
- Do not claim 8 spoken languages. Seven have clips; Mandarin has no released MMS-TTS checkpoint and
  ships text-only, on screen.
- Do not call the seri clip a field recording. It is labelled synthetic until a real one replaces it.
- Do not quote "3.5 billion at risk". No such figure exists in this repo.
- Do not say the endpoint is live. The static demo is live; the Python route is not hosted.

## After recording

1. Upload **public** to YouTube, title it `Lifeline AI — Nebius x NVIDIA Hackathon`, paste the link into
   Devpost.
2. Confirm the duration is **3:00 or less** on the YouTube page, not just in the editor.
3. Listen once with headphones for the three required phrases.
4. `git status` must be clean; push the commit that produced the take.
5. Attach `artifacts/nebius_proof.json`, `artifacts/seri_gate.json`, `artifacts/tavily_proof.json`.
