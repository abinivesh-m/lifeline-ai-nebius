# Proof artefacts

Everything in this folder is a real capture. Nothing is rendered to look like
something it is not, and nothing here is a mock-up of a result.

| File | What it is | Status |
| --- | --- | --- |
| `nvidia_smi.txt` | Raw `nvidia-smi` output from the demo laptop (RTX 3050 6 GB) | real |
| `gpu_6gb_nvidia_smi.png` | The same output rendered, titled as *not* Task Manager | real |
| `offline_run.txt` | Full 8-step `LIFELINE_OFFLINE=1 python agent.py --yes` transcript | real |
| `protocols.txt` | Snake-boat relay + ant-pheromone output | real |
| `gpu_6gb_taskmgr.png` | Task Manager showing `RTX 3050 6GB` and `0.0/6.0 GB` | **capture needed** |
| `offline_proof.mp4` | Task Manager + `nvidia-smi` + airplane mode + offline run | **capture needed** |

The live model evidence is JSON, not video, because a JSON trace is harder to
fake and easier to check:

| File | What it is |
| --- | --- |
| `artifacts/nebius_proof.json` | Three real Token Factory calls (fast / deep / decision), model ids, token counts, per-call cost, 70/30 validator PASS, citation ids |
| `artifacts/nebius_proof_rejected.json` | A kept rejection: the validator refusing a proposal. Proof the check is real |
| `artifacts/tavily_proof.json` | 37 extracted URLs, 45 images, 10 answers, 2 maps, 3 crawled pages, 9/17 claims accepted, 132 credits |
| `artifacts/multilingual_payloads.json` | 8 locales × 3 payloads, each with the model that drafted it, the reviewer verdict and the code check |
| `artifacts/seri_gate.json` | 7 spoken approvals re-classified by Nemotron 3 and sealed in the hash chain |
| `artifacts/benchmark.json` | Local engine timings (median / p95 over 500 loops) and the recorded model latencies |

## Why the two screen captures are not here yet

They require the desktop session that owns the GPU: Task Manager's Performance
tab and a screen recorder. A generated image would be a fabrication, so the repo
keeps the raw `nvidia-smi` text and labels the two captures as pending. They are
not needed to reproduce any number: every model number in the README comes from
a JSON trace that ships with the repo.

## How to capture them

1. Open Task Manager → Performance → GPU. Confirm the header reads
   `NVIDIA GeForce RTX 3050 6GB Laptop GPU` and the dedicated-memory row reads
   `0.0/6.0 GB`. Screenshot to `artifacts/proof/gpu_6gb_taskmgr.png`.
2. Close Chrome/YouTube first: the machine runs at ~94% RAM during recording,
   and a stutter will read as a broken demo.
3. Record `offline_proof.mp4` with the window visible:
   `nvidia-smi` → airplane mode on → `set LIFELINE_OFFLINE=1` →
   `python agent.py --yes` → all eight steps.
4. Re-shoot the live model evidence any time with
   `python scripts/nebius_proof.py`; it rewrites `artifacts/nebius_proof.json`
   with fresh latencies and the same validator.

The `.gitignore` already allows `artifacts/proof/*.mp4` and
`artifacts/audio/report_01.wav` once they exist.
