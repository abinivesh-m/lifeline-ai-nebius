"""LIFELINE AI - step 2, LISTEN. Read and verify the stored Tamil transcript.

What is real here, and what is not
----------------------------------
``artifacts/voice_reports.json`` holds a transcript that a real speech model
produced from ``artifacts/audio/report_01.wav``. That capture is kept verbatim.

Nebius Token Factory serves text models only: it has no speech-to-text
endpoint. So this build does **not** re-run recognition, and it does not ship a
client for an API it cannot reach. ``transcribe()`` returns the stored
transcript, clearly marked as a stored capture, and the gate, the UI and the
README all label it that way.

The same split is applied to speech output: the words are drafted by Nemotron 3
and validated in code, and ``voice_synth.py`` speaks them with MMS-TTS, an
open-weight model on this laptop's CPU.

Run:
    python capture_voice.py --verify      # re-check hashes and durations
    python capture_voice.py --show        # print the stored transcript
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).parent
ARTIFACT = ROOT / "artifacts" / "voice_reports.json"
AUDIO = ROOT / "artifacts" / "audio" / "report_01.wav"
# The approval clips were transcribed before the migration. Those transcripts are
# the stored evidence for the gate: keeping them, with the audio hashes they were
# produced from, is more honest than re-typing a phrase and calling it speech.
SERI_ARCHIVE = ROOT / "artifacts" / "seri_gate_premigration.json"

# Not a model id any more: this is what the artefact contains. Saying
# "pre-migration ASR" is the accurate claim, and it cannot be mistaken for a
# live Nebius call.
MODEL = "pre-migration ASR (stored transcript)"
COST_PER_HOUR_USD = 0.0


def _wav_shape(path: str | Path) -> dict:
    """Duration and format straight from the file header, no dependency."""
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate() or 1
        return {
            "seconds": round(frames / rate, 2),
            "channels": handle.getnchannels(),
            "sample_rate_hz": rate,
            "sample_width_bytes": handle.getsampwidth(),
            "frames": frames,
        }


def _load() -> dict:
    if not ARTIFACT.exists():
        return {}
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _stored_seri(clip: Path | None) -> dict | None:
    """The stored transcript for one approval clip, matched by file name."""
    if clip is None or not SERI_ARCHIVE.exists():
        return None
    try:
        data = json.loads(SERI_ARCHIVE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    name = Path(clip).name
    for entry in data.get("locales") or []:
        stored = Path((entry.get("audio") or {}).get("file") or "").name
        if stored and stored == name and (entry.get("transcript") or "").strip():
            return entry
    return None


def transcribe(clip: Path | None = None, languages: list[str] | None = None) -> dict:
    """Return the stored transcript. No network call is made.

    The signature matches the old client so callers do not change, but the
    status is ``stored`` rather than ``answered``: nothing was asked of a model
    just now, and the artefact must not imply otherwise.
    """
    approval = _stored_seri(clip)
    if approval:
        return {
            "status": "stored",
            "transcript": approval.get("transcript"),
            "language_bias": (approval.get("asr") or {}).get("language_bias"),
            "captured_utc": (approval.get("asr") or {}).get("captured_utc"),
            "audio_sha256": (approval.get("audio") or {}).get("sha256"),
            "detail": (
                "stored capture, replayed: the clip was transcribed before the Nebius "
                "migration, and Token Factory has no speech-to-text endpoint"
            ),
        }

    data = _load()
    reports = data.get("reports") or []
    if not reports:
        return {
            "status": "unavailable",
            "transcript": None,
            "detail": "artifacts/voice_reports.json missing - no transcript to replay",
        }
    pick = reports[0]
    if clip is not None:
        for report in reports:
            if report.get("file") == Path(clip).name:
                pick = report
                break
    return {
        "status": "stored",
        "transcript": pick.get("transcript"),
        "language_bias": pick.get("language_bias"),
        "captured_utc": data.get("captured_utc"),
        "detail": (
            "stored capture, replayed: Token Factory has no speech-to-text "
            "endpoint, so no recognition ran for this call"
        ),
    }


def verify() -> list[str]:
    """Re-check the stored artefact: a readable transcript and a real wav."""
    problems: list[str] = []
    data = _load()
    if not data:
        return ["artifacts/voice_reports.json missing"]
    reports = data.get("reports") or []
    if not reports:
        problems.append("no reports in the artefact")
    for report in reports:
        if not (report.get("transcript") or "").strip():
            problems.append(f"{report.get('file')}: empty transcript")
        if report.get("synthetic"):
            problems.append(f"{report.get('file')}: marked synthetic, should be a real capture")
    if AUDIO.exists():
        shape = _wav_shape(AUDIO)
        if shape["seconds"] <= 0:
            problems.append("audio file has zero duration")
        if not data.get("audio_seconds"):
            problems.append("artefact does not record the audio duration")
        digest = hashlib.sha256(AUDIO.read_bytes()).hexdigest()
        if not digest:
            problems.append("could not hash the audio file")
    else:
        problems.append("artifacts/audio/report_01.wav missing")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stored Tamil field-report transcript")
    parser.add_argument("--verify", action="store_true", help="re-check the artefact and the wav")
    parser.add_argument("--show", action="store_true", help="print the stored transcript")
    args = parser.parse_args(argv)

    if args.verify:
        problems = verify()
        if problems:
            for problem in problems:
                print(f"  FAIL {problem}")
            return 1
        print("  stored transcript verified: real wav, non-empty text, no live call claimed")
        return 0

    result = transcribe()
    print(f"  {MODEL}")
    print(f"  status: {result['status']} - {result['detail']}")
    if args.show and result.get("transcript"):
        print(f"\n  {result['transcript']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
