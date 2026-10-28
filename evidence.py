"""TAVILY EVIDENCE - retrieved, never remembered.

The engine's numbers come from ``town.json``. Everything *outside* the town -
what a landslide does to a road, what a hospital generator actually needs, how
often this pattern repeats - has to come from the open web, and it has to be
checkable by a judge without trusting us.

This module makes four Tavily calls for that, and records the receipt:

    search   POST /search    search_depth=advanced, answer, raw_content, images
    extract  POST /extract   extract_depth=advanced over the shortlisted URLs
    map      POST /map       the site structure of the authority we cite
    crawl    POST /crawl     optional, one hop, only if a page needs following

Three rules make the output evidence instead of decoration:

1. A quote is a *substring* of the text we fetched. ``find_quote`` searches the
   retrieved body and returns the span; nothing is paraphrased into existence.
2. A source only counts if ``/extract`` succeeded for its URL. A search hit is
   a lead, not a source.
3. A dated claim needs a publication date inside the window. No date, no pass -
   the row is kept and shown as ``undated`` rather than silently dropped.

Every response is cached by request hash, so the proof artefact can be rebuilt
offline and re-running it costs zero credits. Credits actually spent are read
from the API's own ``usage`` field, not from a table we typed.

CLI:
    python evidence.py --mode scenario      # Dec 2023 Kottur replan context
    python evidence.py --mode live          # today's web, freshness-checked
    python evidence.py --mode scenario --replay   # cache only, no network
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
CACHE = ARTIFACTS / "tavily_cache"
PROOF = ARTIFACTS / "tavily_proof.json"
USAGE = ARTIFACTS / "tavily_usage.json"
ENV_PATH = ROOT / ".env"

DEFAULT_BASE = "https://api.tavily.com"

# Published costs, from docs.tavily.com/documentation/api-credits. Used only to
# price a cached replay; live calls are priced from the response's own `usage`.
COST = {"search": {"basic": 1, "advanced": 2}, "extract": {"basic": 1, "advanced": 2}, "map": 1}

# Two modes, never mixed. Scenario is the 2023 event being replanned; live is
# whatever the web says today. Blending them would let a 2023 figure pass as
# current, which is the exact failure this module exists to prevent.
WINDOWS = {"scenario": ("2023-11-01", "2024-02-29"), "live": None}
LIVE_FRESH_DAYS = 45

# Authoritative domains first. `include_domains` keeps the result set from
# collapsing into social posts; if it returns nothing we fall back to open web
# and say so in the artefact.
DOMAINS = [
    "thehindu.com",
    "newindianexpress.com",
    "timesofindia.indiatimes.com",
    "indianexpress.com",
    "ndtv.com",
    "reuters.com",
    "bbc.com",
    "aljazeera.com",
    "worldbank.org",
    "who.int",
    "un.org",
    "reliefweb.int",
    "gov.in",
    "nic.in",
]

QUERIES = {
    # Scenario mode replays the 2023 window, so every source must be dated
    # inside it. These are the documented events of the same class the town
    # simulates: a highway cut by a landslide, a grid failure, a rescue that
    # ran on generators.
    "scenario": [
        "Uttarakhand tunnel collapse November 2023 41 workers rescued",
        "Chennai floods December 2023 power supply disrupted relief camps",
        "landslide closes national highway India 2023 vehicles stranded",
        "hospital diesel generator power outage during disaster",
        "fuel supply disruption disaster relief diesel shortage",
    ],
    # Live mode is today's web: the same road the scenario is set on, checked
    # against reality this week. Freshness window, not a 2023 date range.
    "live": [
        "Pollachi Valparai ghat road landslide boulders vehicles stranded",
        "Pollachi Valparai ghat road reopens landslide",
        "landslide cuts off mountain town highway rescue",
        "hospital diesel generator fuel outage disaster response",
        "flood road closure fuel supply disruption town",
    ],
}

# A source below this Tavily relevance score is a lead, not evidence. The first
# run proved why: without a floor, a UK motorway story "supported" a road-closure
# claim purely because both contained the word "closed".
RELEVANCE_FLOOR = 0.20

# Mechanism claims are timeless ("generators run on diesel"); event claims are
# not ("this road closed in December 2023"). Only the second kind needs a date
# inside the window.
MECHANISM_TOPICS = ("power_loss", "fuel_logistics")

# Live claims must be about *this* road. Scenario claims must be about the same
# class of event in the same country. One token list cannot do both: "india" is
# right for a comparable event and far too loose for today's local condition.
LOCAL_REGIONS = ("pollachi", "valparai", "coimbatore", "tamil nadu", "nilgiris", "anamalai", "kerala")
COMPARABLE_REGIONS = ("india", "kerala", "tamil nadu", "uttarakhand", "chennai")


def region_terms(mode: str = "live") -> tuple[str, ...]:
    """Region is configuration, not code.

    LIFELINE_REGION_TERMS overrides the local set, so pointing the product at
    another town is an env change, not a patch.
    """
    raw = os.environ.get("LIFELINE_REGION_TERMS", "")
    values = tuple(part.strip().lower() for part in raw.split(",") if part.strip())
    if values:
        return values
    return LOCAL_REGIONS if mode == "live" else COMPARABLE_REGIONS

# Page furniture that survives extraction and poisons a quotation.
NOISE = ("published on", "sign up", "subscribe", "cookie", "advertisement", "read more", "follow us",
         "share this", "all rights reserved", "jump to content", "main menu", "recommended stories",
         "list 1 of", "live live", "trending", "most read", "related articles", "photo gallery",
         "download the app", "newsletter", "whatsapp", "follow the", "stay with us", "also read",
         "click here", "related stories", "app to stay", "share page", "image caption")

CLAIMS = [
    {
        "topic": "road_cut",
        "needs": ("landslide",),
        "terms": [("road", "closed"), ("highway", "blocked"), ("traffic", "diverted"), ("ghat", "closed"), ("road", "blocked")],
    },
    {
        "topic": "power_loss",
        "needs": ("power",),
        "terms": [("power", "supply"), ("electricity",), ("power", "cut"), ("power", "outage")],
    },
    {
        "topic": "fuel_logistics",
        "needs": ("diesel",),
        "terms": [("diesel", "generator"), ("diesel", "litre"), ("diesel", "liters"), ("fuel", "supply")],
    },
    {
        "topic": "disaster_scale",
        "needs": ("people",),
        "terms": [("people", "evacuated"), ("relief", "camp"), ("workers", "trapped"), ("people", "affected")],
    },
    {
        "topic": "rescue",
        "needs": ("rescue",),
        "terms": [("rescue", "operation"), ("rescue", "workers"), ("rescue", "team"), ("rescue", "drill")],
    },
]


# --------------------------------------------------------------------------- #
# env + transport
# --------------------------------------------------------------------------- #

def load_env(path: Path = ENV_PATH) -> None:
    """Minimal .env reader - the repo has no python-dotenv dependency."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


def configured() -> bool:
    return bool(os.environ.get("TAVILY_API_KEY")) and os.environ.get("LIFELINE_OFFLINE", "0") != "1"


def base_url() -> str:
    return os.environ.get("TAVILY_BASE_URL", DEFAULT_BASE).rstrip("/")


def _cache_path(endpoint: str, payload: dict) -> Path:
    blob = json.dumps({"endpoint": endpoint, "payload": payload}, sort_keys=True).encode("utf-8")
    return CACHE / f"{hashlib.sha256(blob).hexdigest()[:20]}.json"


def _record(endpoint: str, credits: int, seconds: float, request_id: str | None, cached: bool) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    rows = []
    if USAGE.exists():
        try:
            rows = json.loads(USAGE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rows = []
    rows.append(
        {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "endpoint": endpoint,
            "credits": credits,
            "seconds": round(seconds, 2),
            "request_id": request_id,
            "cached": cached,
        }
    )
    USAGE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def post(endpoint: str, payload: dict, replay: bool = False, timeout: float = 120.0) -> dict:
    """One POST, cached by request hash. Raises EvidenceError with the API's message."""
    path = _cache_path(endpoint, payload)
    if path.exists():
        body = json.loads(path.read_text(encoding="utf-8"))
        body["_cached"] = True
        return body
    if replay:
        raise EvidenceError(f"replay: no cached response for {endpoint}")
    if not configured():
        raise EvidenceError("TAVILY_API_KEY missing or LIFELINE_OFFLINE=1")

    started = time.time()
    request = urllib.request.Request(
        base_url() + endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise EvidenceError(f"HTTP {exc.code} {endpoint}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{type(exc).__name__} {endpoint}: {exc}") from exc

    elapsed = time.time() - started
    credits = int((body.get("usage") or {}).get("credits") or 0)
    body["_cached"] = False
    _record(endpoint, credits, elapsed, body.get("request_id"), cached=False)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return body


class EvidenceError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# the four calls
# --------------------------------------------------------------------------- #

def search(
    query: str,
    max_results: int = 6,
    depth: str = "advanced",
    topic: str = "general",
    start_date: str | None = None,
    end_date: str | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    country: str | None = None,
    time_range: str | None = None,
    replay: bool = False,
) -> dict:
    """Advanced search with every context flag on.

    One request returns: ranked results with snippets, a synthesised `answer`,
    full `raw_content` per result, and images with descriptions. Using all four
    is the point - a plan built only on titles is a guess.
    """
    payload: dict = {
        "query": query,
        "search_depth": depth,
        "topic": topic,
        "max_results": max(1, min(20, max_results)),
        "include_answer": True,
        "include_raw_content": True,
        "include_images": True,
        "include_image_descriptions": True,
        "include_usage": True,
    }
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    if country:
        payload["country"] = country
    if time_range:
        payload["time_range"] = time_range
    return post("/search", payload, replay=replay)


def extract(
    urls: list[str],
    query: str | None = None,
    depth: str = "advanced",
    chunks: int = 3,
    images: bool = True,
    replay: bool = False,
) -> dict:
    """Fetch the actual pages. 20 URLs max per call, 2 credits per 5 successes."""
    payload: dict = {
        "urls": urls[:20],
        "extract_depth": depth,
        "include_images": images,
        "include_usage": True,
        "format": "markdown",
    }
    if query:
        payload["query"] = query
        payload["chunks_per_source"] = max(1, min(5, chunks))
    return post("/extract", payload, replay=replay)


def map_site(url: str, instructions: str | None = None, limit: int = 20, replay: bool = False) -> dict:
    """The site's own structure - proves we looked at a source, not one page."""
    payload: dict = {"url": url, "max_depth": 2, "limit": max(1, min(100, limit)), "include_usage": True}
    if instructions:
        payload["instructions"] = instructions
    return post("/map", payload, replay=replay)


def crawl(url: str, instructions: str | None = None, limit: int = 6, replay: bool = False) -> dict:
    """Map + extract in one call. Used when one page is an index, not an article."""
    payload: dict = {
        "url": url,
        "max_depth": 1,
        "limit": max(1, min(20, limit)),
        "extract_depth": "advanced",
        "include_images": False,
        "include_usage": True,
    }
    if instructions:
        payload["instructions"] = instructions
    return post("/crawl", payload, replay=replay)


# --------------------------------------------------------------------------- #
# verification - the part that makes it evidence
# --------------------------------------------------------------------------- #

def normalise(text: str) -> str:
    """Whitespace, case and markdown noise are not meaning. Normalise both sides."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"[#*_>`\[\]()!]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def clean_body(text: str) -> str:
    """Strip the page furniture extraction leaves behind, keep the prose."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)          # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)        # links -> text
    text = re.sub(r"(?m)^\s*#{1,6}\s*", " ", text)              # heading markers
    text = text.replace("|", " ")
    return re.sub(r"\s+", " ", text).strip()


def find_quote(text: str, terms: tuple[str, ...], max_chars: int = 400) -> str | None:
    """Return a literal passage from `text` containing every term, or None.

    Passages are 1-3 consecutive sentences, so a claim whose words are spread
    across a paragraph still matches - but the result is still a slice of the
    source, never a sentence of our own. Nav bars, cookie banners and "related
    stories" rails are rejected: a quotation has to be prose.
    """
    if not text:
        return None
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_body(text)) if s.strip()]
    for index, sentence in enumerate(sentences):
        if len(sentence.split()) < 8:
            continue
        for span in (1, 2, 3):
            passage = " ".join(sentences[index: index + span])
            if len(passage) > max_chars * 2:
                break
            low = passage.lower()
            if any(noise in low for noise in NOISE) or re.search(r"\blist \d+ of \d+\b", low):
                continue
            clean = normalise(passage)
            if all(normalise(term) in clean for term in terms):
                return passage[:max_chars]
    return None


def source_in_region(url: str, title: str | None, mode: str = "live") -> bool:
    """Region is a property of the source, not of the sentence.

    A photo gallery about Indian tunnel workers never says "India" in the
    sentence we quote, while a Chinese mine story can mention India in a
    sidebar. Checking URL + title gets both cases right.
    """
    return in_region(f"{url} {title or ''}", mode)


def in_region(text: str, mode: str = "live") -> bool:
    clean = normalise(text)
    return any(region in clean for region in region_terms(mode))


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for candidate in (text, text[:10], text[:16]):
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%a, %d %b %Y %H:%M:%S %Z"):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match[1]), int(match[2]), int(match[3]))
        except ValueError:
            return None
    return None


def window_ok(published: date | None, mode: str) -> tuple[bool, str]:
    if published is None:
        return False, "undated"
    if mode == "scenario":
        start, end = (date.fromisoformat(value) for value in WINDOWS["scenario"])
        return (start <= published <= end, "in-window" if start <= published <= end else "out-of-window")
    limit = date.today() - timedelta(days=LIVE_FRESH_DAYS)
    return (published >= limit, "fresh" if published >= limit else "stale")


MONTHS = {name: index for index, name in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def date_from_url(url: str) -> date | None:
    """Many outlets put the publication date in the path and nowhere else.

    The Hindu's `.../2026/Oct/22/slug` is a date the source itself asserts, so
    reading it is citation, not inference.
    """
    match = re.search(r"/(20\d{2})/([A-Za-z]{3,9})/(\d{1,2})/", url)
    if match:
        month = MONTHS.get(match[2][:3].lower())
        if month:
            try:
                return date(int(match[1]), month, int(match[3]))
            except ValueError:
                return None
    match = re.search(r"/(20\d{2})/(\d{2})/(\d{2})/", url)
    if match:
        try:
            return date(int(match[1]), int(match[2]), int(match[3]))
        except ValueError:
            return None
    return None


def date_from_body(text: str) -> date | None:
    """Last resort: the byline the page prints about itself."""
    window = (text or "")[:3000]
    match = re.search(r"(?:published|updated)[^0-9]{0,20}(\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2})", window, re.I)
    return parse_date(match[1]) if match else None


def verify(claim: str, quote: str, url: str, body: str, published: date | None, mode: str, relevant: bool = True,
           score: float | None = None, region_ok: bool = True, timely: bool = True) -> dict:
    """Five independent checks, with a date rule that depends on the claim type.

    An *event* claim ("this road closed in December 2023") must carry a date
    inside the window. A *mechanism* claim ("hospital generators run on diesel")
    is timeless, so it can pass undated - but still has to be fetched, relevant
    and regional. Labeling the type is what stops a 2023 figure being quoted as
    current.
    """
    literal = normalise(quote) in normalise(body) if quote and body else False
    fetched = bool(body)
    dated, date_state = window_ok(published, mode)
    if not timely and date_state == "undated":
        date_state = "undated (mechanism)"
    accepted = bool(literal and fetched and relevant and region_ok and (dated or not timely))
    if not relevant:
        verdict = f"rejected: relevance {score if score is not None else '?'} below {RELEVANCE_FLOOR}"
    elif not region_ok:
        verdict = "rejected: no regional anchor"
    elif not literal:
        verdict = "rejected: quote not in fetched text"
    elif not fetched:
        verdict = "rejected: url not fetched"
    elif not dated and timely:
        verdict = f"rejected: {date_state}"
    else:
        verdict = "accepted"
    return {
        "claim": claim,
        "quote": quote,
        "url": url,
        "published": published.isoformat() if published else None,
        "relevance": score,
        "quote_literal": literal,
        "url_fetched": fetched,
        "date_check": date_state,
        "region_ok": region_ok,
        "accepted": accepted,
        "verdict": verdict,
    }


# --------------------------------------------------------------------------- #
# harvest
# --------------------------------------------------------------------------- #

def harvest(mode: str, replay: bool = False) -> dict:
    """Run the pipeline for one mode and return a proof-shaped dict."""
    if mode not in QUERIES:
        raise ValueError(f"mode must be one of {sorted(QUERIES)}")
    started = time.time()
    credits_before = usage_summary()["credits"]
    searches: list[dict] = []
    leads: list[str] = []

    start, end = (WINDOWS["scenario"] if mode == "scenario" else (None, None))
    for query in QUERIES[mode]:
        try:
            response = search(
                query,
                max_results=8,
                topic="news",
                start_date=start,
                end_date=end,
                time_range="month" if mode == "live" else None,
                include_domains=DOMAINS,
                replay=replay,
            )
        except EvidenceError as exc:
            searches.append({"query": query, "error": str(exc), "results": []})
            continue
        results = response.get("results") or []
        if not results and DOMAINS:
            # Domain filter was too tight for this query; retry unfiltered and
            # record that we did, rather than reporting zero evidence.
            try:
                response = search(query, max_results=8, topic="news", start_date=start, end_date=end, replay=replay)
                results = response.get("results") or []
            except EvidenceError as exc:
                searches.append({"query": query, "error": str(exc), "results": []})
                continue
        searches.append(
            {
                "query": query,
                "answer": response.get("answer"),
                "images": response.get("images") or [],
                "response_time": response.get("response_time"),
                "results": results,
            }
        )
    # Interleave leads across queries before the batch. Taking the first 20 in
    # discovery order let the first two queries eat the whole extract budget,
    # so road/power/fuel were never actually fetched.
    per_query = [[row["url"] for row in (s.get("results") or []) if row.get("url")] for s in searches]
    leads = []
    for rank in range(max((len(urls) for urls in per_query), default=0)):
        for urls in per_query:
            if rank < len(urls) and urls[rank] not in leads:
                leads.append(urls[rank])

    # One extract call, advanced depth: does each URL actually open?
    extracted: dict[str, dict] = {}
    failed: list[dict] = []
    if leads:
        try:
            batch = extract(leads[:20], query=QUERIES[mode][0], replay=replay)
            for row in batch.get("results") or []:
                extracted[row["url"]] = row
            failed = batch.get("failed_results") or []
        except EvidenceError as exc:
            failed = [{"url": url, "error": str(exc)} for url in leads]

    # One map call on the most authoritative domain we actually reached.
    mapped: dict | None = None
    root = next((url for url in extracted if any(domain in url for domain in DOMAINS)), None)
    if root:
        parts = urllib.parse.urlsplit(root)
        try:
            mapped = map_site(f"{parts.scheme}://{parts.netloc}", instructions="disaster and emergency coverage", replay=replay)
        except EvidenceError as exc:
            mapped = {"error": str(exc)}

    # One crawl on the same authority: map + extract in a single call, so the
    # proof shows the site was explored, not just one lucky article.
    crawled: dict | None = None
    if root:
        parts = urllib.parse.urlsplit(root)
        try:
            crawled = crawl(
                f"{parts.scheme}://{parts.netloc}",
                instructions="emergency, disaster, landslide and relief coverage",
                limit=5,
                replay=replay,
            )
        except EvidenceError as exc:
            crawled = {"error": str(exc)}

    # Pull a literal quote per topic from each fetched body.
    excerpts: list[dict] = []
    for url, row in extracted.items():
        body = row.get("raw_content") or ""
        meta = next((r for s in searches for r in s["results"] if r.get("url") == url), {})
        published = parse_date(meta.get("published_date")) or date_from_url(url) or date_from_body(body)
        score = meta.get("score")
        relevant = float(score or 0) >= RELEVANCE_FLOOR
        regional = source_in_region(url, meta.get("title"), mode)
        for claim in CLAIMS:
            for terms in claim["terms"]:
                quote = find_quote(body, tuple(claim["needs"]) + tuple(terms))
                if quote:
                    excerpts.append(
                        {
                            "topic": claim["topic"],
                            "terms": list(terms),
                            "title": meta.get("title"),
                            **verify(
                                claim["topic"], quote, url, body, published, mode,
                                relevant=relevant, score=score, region_ok=regional,
                                timely=claim["topic"] not in MECHANISM_TOPICS,
                            ),
                        }
                    )
                    break
    excerpts.sort(key=lambda row: (not row["accepted"], -(row.get("relevance") or 0), row["topic"], row["url"]))

    # Real credits: the delta in the ledger the API itself filled in.
    credits_after = usage_summary()["credits"]
    proof = {
        "schema": 1,
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window": {"start": start, "end": end} if mode == "scenario" else {"fresh_days": LIVE_FRESH_DAYS},
        "api": {"base": base_url(), "search_depth": "advanced", "extract_depth": "advanced"},
        "region": list(region_terms(mode)),
        "usage": {"credits_this_run": credits_after - credits_before, "credits_to_date": credits_after},
        "totals": {
            "queries": len(QUERIES[mode]),
            "leads": len(leads),
            "urls_fetched": len(extracted),
            "urls_failed": len(failed),
            "images": sum(len(s.get("images") or []) for s in searches),
            "answers": sum(1 for s in searches if s.get("answer")),
            "maps": 1 if mapped and not mapped.get("error") else 0,
            "crawls": len(crawled.get("results") or []) if crawled and not crawled.get("error") else 0,
            "claims_checked": len(excerpts),
            "claims_accepted": sum(1 for row in excerpts if row["accepted"]),
            "wall_clock_s": round(time.time() - started, 2),
        },
        "searches": searches,
        "extract": {"attempted": len(leads[:20]), "failed": failed, "urls": list(extracted)},
        "map": mapped,
        "crawl": crawled,
        "excerpts": excerpts,
    }
    return proof


def usage_summary() -> dict:
    if not USAGE.exists():
        return {"calls": 0, "credits": 0}
    rows = json.loads(USAGE.read_text(encoding="utf-8"))
    return {
        "calls": len(rows),
        "credits": sum(int(r.get("credits") or 0) for r in rows),
        "cached_replays": sum(1 for r in rows if r.get("cached")),
        "last": rows[-1] if rows else None,
    }


def combine(paths: dict[str, Path] | None = None) -> dict:
    """Merge the two per-mode proofs into one artefact, keeping the modes apart."""
    paths = paths or {"scenario": ARTIFACTS / "tavily_proof_scenario.json",
                      "live": ARTIFACTS / "tavily_proof_live.json"}
    modes, totals = {}, {}
    order = ("queries", "leads", "urls_fetched", "urls_failed", "images", "answers",
             "maps", "crawls", "claims_checked", "claims_accepted")
    for mode, path in paths.items():
        if not path.exists():
            continue
        body = json.loads(path.read_text(encoding="utf-8"))
        modes[mode] = body
        for key in order:
            totals[key] = totals.get(key, 0) + int(body["totals"].get(key) or 0)
    totals["wall_clock_s"] = round(sum(float(m["totals"].get("wall_clock_s") or 0) for m in modes.values()), 2)
    return {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "api": {"base": base_url(), "search_depth": "advanced", "extract_depth": "advanced"},
        "region": list(region_terms("live")),
        "usage": {"credits_to_date": usage_summary()["credits"], "calls": usage_summary()["calls"]},
        "totals": totals,
        "modes": modes,
        "rule": "Mode 1 (scenario) and Mode 2 (live) are stored and rendered separately, never blended.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieve and verify web evidence with Tavily.")
    parser.add_argument("--mode", choices=sorted(QUERIES), default="scenario")
    parser.add_argument("--replay", action="store_true", help="read the cache, never hit the network")
    parser.add_argument("--out", default=None)
    parser.add_argument("--combine", action="store_true", help="merge both mode proofs into one artefact")
    args = parser.parse_args(argv)

    load_env()

    if args.combine:
        merged = combine()
        PROOF.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
        totals = merged["totals"]
        print(f"combined: {totals['urls_fetched']} URLs fetched, {totals['images']} images, "
              f"{totals['answers']} answers, {totals['maps']} map, {totals['crawls']} crawl, "
              f"{totals['claims_accepted']}/{totals['claims_checked']} claims accepted")
        print(f"written: {PROOF}")
        return 0

    out = Path(args.out or ARTIFACTS / f"tavily_proof_{args.mode}.json")
    try:
        proof = harvest(args.mode, replay=args.replay)
    except (EvidenceError, ValueError) as exc:
        print(f"evidence: {exc}", file=sys.stderr)
        return 1

    # Never overwrite a good artefact with an empty one. A cache miss during a
    # replay once replaced 18 fetched sources with zero; this is the guard.
    if proof["totals"]["leads"] == 0 or not proof["searches"]:
        print("evidence: no leads returned - keeping the existing artefact", file=sys.stderr)
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8")

    totals = proof["totals"]
    print(f"{proof['mode']}: {totals['leads']} leads, {totals['urls_fetched']} fetched, "
          f"{totals['images']} images, {totals['answers']} answers, {totals['maps']} map, "
          f"{totals['claims_accepted']}/{totals['claims_checked']} claims accepted")
    for row in proof["excerpts"][:6]:
        print(f"  [{row['verdict']}] {row['topic']}: {row['url']}")
        if row["quote"]:
            print(f"    \"{row['quote'][:140]}\"")
    print(f"usage: {json.dumps(usage_summary())}")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
