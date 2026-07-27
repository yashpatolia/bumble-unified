"""Answers free-form Hypixel Skyblock questions using the wiki + Claude.

Ports the standalone skyblock-info CLI project into a single lib module: fetches and
locally caches wiki pages (skyblock mechanics get patched, so pages expire after a TTL
rather than being cached forever), matches a question to the right page(s), and asks
Claude to answer using only that page content. Powers the in-game `.q` command.
"""

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import anthropic
import requests
from bs4 import BeautifulSoup

from config import ANTHROPIC_API_KEY

WIKI_BASE = "https://hypixelskyblock.minecraft.wiki"
API_URL = f"{WIKI_BASE}/api.php"

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
CACHE_FILE = CACHE_DIR / "wiki_cache.json"
TITLES_CACHE_FILE = CACHE_DIR / "titles_cache.json"
DEFAULT_TTL_DAYS = 14  # re-fetch every 2 weeks; Skyblock patches change pages
TITLES_TTL_SECONDS = 30 * 24 * 3600  # the set of page titles churns slower than page content

USER_AGENT = "bumble-bridge-bot/1.0 (wiki Q&A)"
MODEL = "claude-haiku-4-5"

SYSTEM_INSTRUCTIONS = """You answer questions about Hypixel Skyblock using ONLY the wiki page content given below.
Your answer will be typed directly into Minecraft chat, so it must be plain prose only.

Rules:
- Write the whole answer as flowing sentences -- never a list, bullet points, headers, or markdown (no *, -, #, numbered lists).
  Fold quantities and names into the sentence itself, e.g. "it needs 25,600 Iron Ingots, 20,480 Titanium, and 358,400 Diamonds" rather than a list.
- Be as short as possible without dropping any information the question asked for. Skip caveats and details the question didn't ask about.
- If a mechanic mentioned on the page (RNG, dungeon score, floor requirements, etc.) affects the answer, fold it into the same sentence briefly.
- If the given content doesn't fully answer the question but one of the linked pages listed at the end of the user's message likely does, respond with NOTHING but a single line: NEED_PAGE: <exact title from that list>
  Do not add any other text before or after that line. Only do this once per question -- do not ask for a page a second time.
- If you don't know, or the content doesn't cover it, say so plainly in one short sentence. Never guess or use outside knowledge.
- Hypixel Skyblock changes over time. If the content looks like it may describe an outdated or removed mechanic, note that briefly in the same sentence."""

NEED_PAGE_RE = re.compile(r"NEED_PAGE:\s*(.+)")

# Filler words stripped when falling back to network search on an unresolved query --
# irrelevant to local substring/overlap matching, which works on raw text.
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "of", "in", "on", "at", "to", "for",
    "what", "whats", "how", "does", "do", "did", "can", "could", "would", "should",
    "and", "or", "with", "from", "about", "me", "i", "you", "it", "its", "this", "that",
}

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


@dataclass
class WikiPage:
    title: str
    content: str
    links: list[str]
    fetched_at: float


def _load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _get_all_titles(ttl_seconds: float = TITLES_TTL_SECONDS, force_refresh: bool = False) -> list[str]:
    """Return every main-namespace page title, cached locally so this only hits the network occasionally."""
    if TITLES_CACHE_FILE.exists() and not force_refresh:
        try:
            cached = json.loads(TITLES_CACHE_FILE.read_text(encoding="utf-8"))
            if time.time() - cached["fetched_at"] < ttl_seconds:
                return cached["titles"]
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    titles: list[str] = []
    params = {"action": "query", "list": "allpages", "aplimit": "max", "apnamespace": 0, "format": "json"}
    while True:
        resp = requests.get(API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        titles.extend(p["title"] for p in data.get("query", {}).get("allpages", []))
        cont = data.get("continue")
        if not cont:
            break
        params = {**params, **cont}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TITLES_CACHE_FILE.write_text(
        json.dumps({"titles": titles, "fetched_at": time.time()}), encoding="utf-8"
    )
    return titles


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", text.lower())


def _match_titles(question: str, titles: list[str], limit: int = 3) -> list[str]:
    """Find known page titles mentioned verbatim in the question -- no API call involved.

    A question can name more than one entity (e.g. "how does the RNG meter affect
    Necron's Handle drop rate") -- return every non-overlapping match rather than just
    the single best one, so both pages get fetched up front instead of relying on the
    model to notice the cross-reference and ask for a second page.
    """
    normalized_question = _normalize(question)
    candidates = []  # (matched_span_text, title)
    for title in titles:
        normalized_title = _normalize(title)
        if normalized_title and normalized_title in normalized_question:
            candidates.append((normalized_title, title))

    # Drop matches that are wholly contained in another match (e.g. don't also count
    # "Necron" if "Necron's Handle" already matched) -- keep the more specific title.
    candidates.sort(key=lambda c: len(c[0]), reverse=True)
    kept: list[tuple[str, str]] = []
    for span, title in candidates:
        if not any(span in kept_span for kept_span, _ in kept):
            kept.append((span, title))

    return [title for _, title in kept[:limit]]


def _strip_stopwords(question: str) -> str:
    words = [w for w in re.findall(r"[a-z0-9']+", question.lower()) if w not in _STOPWORDS]
    return " ".join(words) or question


def _search_title(query: str) -> Optional[str]:
    """Resolve a near-title query (e.g. an item/mob/mechanic name) to an exact wiki page title."""
    resp = requests.get(
        API_URL,
        params={"action": "opensearch", "search": query, "limit": 1, "namespace": 0, "format": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    titles = resp.json()[1]
    if titles:
        return titles[0]

    # Fall back to full-text search for queries that aren't close to an exact title.
    resp = requests.get(
        API_URL,
        params={"action": "query", "list": "search", "srsearch": query, "srlimit": 1, "format": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("query", {}).get("search", [])
    return results[0]["title"] if results else None


def _fetch_from_wiki(title: str) -> WikiPage:
    resp = requests.get(
        API_URL,
        params={"action": "parse", "page": title, "prop": "text|links", "format": "json", "redirects": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise ValueError(f"Wiki page not found: {title}")

    parsed = data["parse"]
    html = parsed["text"]["*"]
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "sup"]):
        tag.decompose()
    for tag in soup.select("table.navbox, .mw-editsection, .reference"):
        tag.decompose()
    content = soup.get_text(separator="\n", strip=True)

    # Existing (blue) links carry an "exists" key; red links to missing pages don't.
    links = [link["*"] for link in parsed.get("links", []) if link.get("ns") == 0 and "exists" in link]
    links = [l for l in links if not l.lower().startswith("category:")]

    return WikiPage(title=parsed["title"], content=content, links=links, fetched_at=time.time())


def _get_page(title: str, ttl_seconds: float, force_refresh: bool = False) -> WikiPage:
    cache = _load_cache()
    cached = cache.get(title)
    if cached and not force_refresh:
        age = time.time() - cached["fetched_at"]
        if age < ttl_seconds:
            return WikiPage(**cached)

    page = _fetch_from_wiki(title)
    cache[page.title] = asdict(page)
    if title != page.title:
        cache[title] = asdict(page)  # also cache under the alias that was searched
    _save_cache(cache)
    return page


def _page_block(page: WikiPage) -> dict:
    return {"type": "text", "text": f"=== {page.title} ===\n{page.content}"}


def _ask(question: str, pages: list[WikiPage]) -> str:
    # Only two cache_control breakpoints: one after the (always-identical) instructions,
    # one at the very end. That's enough to cache the whole prefix and stays well under
    # the API's 4-breakpoint limit even when a NEED_PAGE hop adds another page block.
    system = [{"type": "text", "text": SYSTEM_INSTRUCTIONS, "cache_control": {"type": "ephemeral"}}]
    system += [_page_block(p) for p in pages]
    if system:
        system[-1] = {**system[-1], "cache_control": {"type": "ephemeral"}}

    user_content = question
    all_links = sorted({link for p in pages for link in p.links})
    if all_links:
        user_content += "\n\n(Pages linked from the above, in case you need one: " + ", ".join(all_links[:80]) + ")"

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    return next((b.text for b in response.content if b.type == "text"), "").strip()


def answer_question(question: str, ttl_days: float = DEFAULT_TTL_DAYS, refresh: bool = False) -> str:
    """Answer a free-form Skyblock question using wiki content, chat-ready plain prose."""
    ttl_seconds = ttl_days * 24 * 3600

    all_titles = _get_all_titles()
    matched_titles = _match_titles(question, all_titles)
    if not matched_titles:
        fallback = _search_title(_strip_stopwords(question)) or _search_title(question)
        if not fallback:
            return "Couldn't find a wiki page matching that. Try rephrasing."
        matched_titles = [fallback]

    pages = [_get_page(t, ttl_seconds=ttl_seconds, force_refresh=refresh) for t in matched_titles]
    reply = _ask(question, pages)

    match = NEED_PAGE_RE.search(reply)
    if match:
        needed_title = match.group(1).strip().strip('"\'.')
        try:
            second_page = _get_page(needed_title, ttl_seconds=ttl_seconds, force_refresh=refresh)
            reply = _ask(question, pages + [second_page])
        except ValueError:
            pass  # linked page didn't resolve -- fall back to the first-pass answer

    return reply
