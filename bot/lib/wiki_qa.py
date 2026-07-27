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
from bs4 import BeautifulSoup, NavigableString, Tag

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

SYSTEM_INSTRUCTIONS = """You answer questions about Hypixel Skyblock. You have two tools: search_wiki (game mechanics,
items, drop rates, recipes, events -- general game knowledge) and get_player_stats (a specific player's live stats).
Use search_wiki for anything general. Use get_player_stats when the question names a specific player/IGN. Use both
if the question needs a player's raw number combined with a wiki page's rules to answer (e.g. a skill level from raw
XP -- get_player_stats gives raw skill XP fields, not computed levels, since Hypixel doesn't return the level
directly; call search_wiki for that skill's page, which documents the XP-per-level breakpoints, and compute the
level yourself from the XP given). Never answer from outside knowledge -- always ground the answer in a tool call.

Your answer will be typed directly into Minecraft chat, which has a strict per-line length limit, so it must be as
short as physically possible -- every extra word is a cost.

Rules:
- Write in telegraphic/caveman style: drop articles (a, an, the), linking verbs (is, are, has), and any word that
  isn't load-bearing for the fact. "Better Together: Dwarven Mines/Crystal Hollows, 20min, +250 Mining Speed +20
  Mining Fortune per player in zone, max 5" not "Better Together is a passive event that occurs in the Dwarven
  Mines and Crystal Hollows and lasts for 20 minutes...". Use commas/slashes instead of "and"/"or" where it still reads clearly.
- Answer in the fewest words that still contain the exact fact asked for. Do not restate the question, add caveats,
  or explain mechanics unless the question specifically asked about that mechanic.
- Only answer exactly what was asked. If asked for one number, give one number -- don't also add related numbers,
  variants, or context nobody asked for.
- No markdown formatting (no *, -, #), but dropped grammar/articles/verbs is fine and preferred over full prose.
- If a tool call fails or comes back empty (page not found, player not found), say so in as few words as possible.
  Never guess or fabricate a number or fact you didn't get from a tool.
- Hypixel Skyblock changes over time. If wiki content looks like it may describe an outdated/removed mechanic, note that briefly.
- Dungeon floors: "F<n>" or "Floor <n>" means Normal Mode; "M<n>" or "Master Mode <n>"/"Master <n>" means Master
  Mode -- a separate, harder floor with its own higher requirements. Wiki tables list these as distinct sections
  (e.g. tagged [Master Mode] per row) -- never answer an M<n> question with an F<n> row's numbers or vice versa.
- If asked to pick/choose/recommend/suggest one option at random from a known, fixed set of game options (a class,
  a weapon, an enchant, etc.), just pick one yourself and say it -- do NOT refuse for lacking a "random number
  generator" tool. Look the valid options up with search_wiki first if you don't already know them from this
  conversation, then commit to a single pick. Never refuse a request just because it's phrased as "random"."""

TOOLS = [
    {
        "name": "search_wiki",
        "description": (
            "Look up a Hypixel Skyblock wiki page by topic/item/mob/mechanic/skill name. Returns the page's full "
            "text content and the titles of pages it links to. Call again with a different query (e.g. a linked "
            "page title) if the first result doesn't answer the question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic to look up, e.g. 'Foraging', \"Necron's Handle\", 'Better Together'"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_player_stats",
        "description": (
            "Fetch a specific player's live Hypixel Skyblock stats: Skyblock level, catacombs level/secrets, slayer "
            "levels, magical power, bank/purse balance, pet score, and raw skill XP (mining/foraging/farming/combat/"
            "etc -- these are unprocessed XP numbers, not levels; pair with search_wiki for the skill's level table "
            "if a computed level is needed). Only call this when the question names a specific in-game player."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ign": {
                    "type": "string",
                    "description": (
                        "The player's Minecraft IGN, copied EXACTLY as it appears in the question -- character "
                        "for character, including any trailing 's'. Minecraft usernames can end in 's' as part "
                        "of the name itself (e.g. 'seazyns'); never strip a trailing 's' as if it were a "
                        "possessive apostrophe-s, the question won't use a real apostrophe for that."
                    ),
                },
            },
            "required": ["ign"],
        },
    },
]

MAX_TOOL_HOPS = 4

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


def _flatten_table(table: Tag) -> str:
    """Render an HTML table as one line per row instead of one line per cell.

    Wiki pages often use a single table for both "Normal Mode" and "Master Mode" rows
    (e.g. Catacombs floor requirements), separated by a full-width section-header row.
    Plain get_text() puts every cell on its own line with no row/column grouping, which
    makes it impossible to tell "Combat Level: 24" (Normal F7) apart from "Combat Level:
    36" (Master M7) once flattened -- this keeps each row's cells, and its section, together.
    """
    lines, headers, section = [], [], ""
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        texts = [c.get_text(" ", strip=True) for c in cells]

        # A lone <th> spanning the row is a section divider (e.g. "Master Mode"), not data.
        if len(cells) == 1 and cells[0].name == "th":
            section = texts[0]
            continue
        if not headers and all(c.name == "th" for c in cells):
            headers = texts
            continue

        if headers and len(texts) == len(headers):
            row = ", ".join(f"{h}: {v}" for h, v in zip(headers, texts) if v)
        else:
            row = " | ".join(t for t in texts if t)
        if not row:
            continue
        lines.append(f"[{section}] {row}" if section else row)

    return "\n".join(lines)


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
    for table in soup.find_all("table"):
        table.replace_with(NavigableString(f"\n{_flatten_table(table)}\n"))
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


def _search_wiki_tool(query: str, ttl_seconds: float, refresh: bool) -> str:
    query = (query or "").strip()
    if not query:
        return "No query given."

    all_titles = _get_all_titles()
    matched = _match_titles(query, all_titles, limit=1)
    title = matched[0] if matched else (_search_title(_strip_stopwords(query)) or _search_title(query))
    if not title:
        return f"No wiki page found for '{query}'."

    try:
        page = _get_page(title, ttl_seconds=ttl_seconds, force_refresh=refresh)
    except ValueError:
        return f"No wiki page found for '{query}'."

    result = f"=== {page.title} ===\n{page.content}"
    if page.links:
        result += "\n\n(Linked pages: " + ", ".join(sorted(set(page.links))[:60]) + ")"
    return result


def _get_player_stats_tool(ign: str) -> str:
    ign = (ign or "").strip()
    if not ign:
        return "No IGN given."

    from player import skyblock, PlayerNotFoundError, HypixelAPIError

    try:
        player = skyblock.Player(username=ign)
    except PlayerNotFoundError:
        return f"No Minecraft account named '{ign}' found."
    except HypixelAPIError as e:
        return f"Hypixel API error looking up '{ign}': {e}"

    stats = {
        "ign": player.username,
        "gamemode": player.gamemode or "Normal",
        "skyblock_level": round(player.level.current, 2),
        "highest_skyblock_level": round(player.level.highest[0], 2),
        "catacombs_level": player.catacombs.level,
        "dungeon_secrets": player.catacombs.secrets,
        "slayer_levels": player.slayers.levels,
        "magical_power": player.magical_power.total,
        "highest_magical_power": player.magical_power.highest,
        "bank_balance": player.bank,
        "purse": player.purse,
        "pet_score": player.pet_score,
        "raw_skill_experience": player.raw_skill_experience,
    }
    return json.dumps(stats)


def _run_tool(name: str, tool_input: dict, ttl_seconds: float, refresh: bool) -> str:
    if name == "search_wiki":
        return _search_wiki_tool(tool_input.get("query", ""), ttl_seconds, refresh)
    if name == "get_player_stats":
        return _get_player_stats_tool(tool_input.get("ign", ""))
    return f"Unknown tool '{name}'."


def answer_question(question: str, ttl_days: float = DEFAULT_TTL_DAYS, refresh: bool = False) -> str:
    """Answer a free-form Skyblock question, letting Claude call the wiki/player-stats tools as needed."""
    ttl_seconds = ttl_days * 24 * 3600
    system = [{"type": "text", "text": SYSTEM_INSTRUCTIONS, "cache_control": {"type": "ephemeral"}}]
    messages = [{"role": "user", "content": question}]
    client = _get_client()

    for _ in range(MAX_TOOL_HOPS):
        response = client.messages.create(
            model=MODEL, max_tokens=250, system=system, tools=TOOLS, messages=messages,
        )
        if response.stop_reason != "tool_use":
            reply = next((b.text for b in response.content if b.type == "text"), "").strip()
            return reply or "Couldn't find an answer for that."

        messages.append({"role": "assistant", "content": response.content})
        tool_results = [
            {"type": "tool_result", "tool_use_id": block.id, "content": _run_tool(block.name, block.input, ttl_seconds, refresh)}
            for block in response.content if block.type == "tool_use"
        ]
        messages.append({"role": "user", "content": tool_results})

    # Ran out of tool hops -- force a final answer with what's already been gathered.
    response = client.messages.create(model=MODEL, max_tokens=150, system=system, messages=messages)
    reply = next((b.text for b in response.content if b.type == "text"), "").strip()
    return reply or "Couldn't find an answer for that."
