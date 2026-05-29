"""Tests for the guild list / online parser functions (lib/guild_list.py)."""
import pytest
from lib.guild_list import parse_guild_list, parse_online_igns


# ── Helpers ────────────────────────────────────────────────────────────────

def igns(members: list) -> list[str]:
    return [m["ign"] for m in members]

def ranks_for(members: list, ign: str) -> str:
    return next(m["rank"] for m in members if m["ign"] == ign)


# ── parse_guild_list ───────────────────────────────────────────────────────

GUILD_LIST_BASIC = [
    "Guild Name: Bumble Kindergarten",
    "------ Baby Bee (2) ------",
    "PlayerAlpha ● PlayerBeta ●",
    "------ Toddler Bee (1) ------",
    "PlayerGamma ●",
    "Online Members: 1",
    "Total Members: 3",
]

def test_parse_guild_list_igns():
    result = parse_guild_list(GUILD_LIST_BASIC)
    assert set(igns(result)) == {"PlayerAlpha", "PlayerBeta", "PlayerGamma"}

def test_parse_guild_list_ranks():
    result = parse_guild_list(GUILD_LIST_BASIC)
    assert ranks_for(result, "PlayerAlpha") == "Baby Bee (2)"
    assert ranks_for(result, "PlayerGamma") == "Toddler Bee (1)"

def test_parse_guild_list_count():
    result = parse_guild_list(GUILD_LIST_BASIC)
    assert len(result) == 3

def test_parse_guild_list_mc_rank_prefixes():
    """[MVP+] and similar prefixes should be stripped, IGN extracted."""
    lines = [
        "------ Sweaty Bee (1) ------",
        "[MVP+] CoolPlayer ●",
        "[VIP+] AnotherPlayer ●",
    ]
    result = parse_guild_list(lines)
    assert set(igns(result)) == {"CoolPlayer", "AnotherPlayer"}

def test_parse_guild_list_multiple_on_one_line():
    """Multiple IGNs on the same line (Hypixel packs them space-separated)."""
    lines = [
        "------ Baby Bee ------",
        "Alpha ● Beta ● Gamma ●",
    ]
    result = parse_guild_list(lines)
    assert set(igns(result)) == {"Alpha", "Beta", "Gamma"}

def test_parse_guild_list_skips_footer_words():
    """'Total', 'Online', 'Members' lines must not appear as IGNs."""
    result = parse_guild_list(GUILD_LIST_BASIC)
    for m in result:
        assert m["ign"] not in {"Total", "Online", "Members", "Guild"}

def test_parse_guild_list_empty():
    assert parse_guild_list([]) == []

def test_parse_guild_list_no_members():
    lines = [
        "Guild Name: Bumble Kindergarten",
        "Online Members: 0",
        "Total Members: 0",
    ]
    assert parse_guild_list(lines) == []

def test_parse_guild_list_mixed_case_ranks():
    lines = [
        "------ Ultimate Bee (1) ------",
        "TopPlayer ●",
    ]
    result = parse_guild_list(lines)
    assert ranks_for(result, "TopPlayer") == "Ultimate Bee (1)"

def test_parse_guild_list_preserves_ign_case():
    lines = [
        "------ Baby Bee ------",
        "xXProPlayerXx ●",
    ]
    result = parse_guild_list(lines)
    assert igns(result) == ["xXProPlayerXx"]

def test_parse_guild_list_short_names_excluded():
    """IGNs must be 3+ chars; 1–2-char tokens get skipped."""
    lines = [
        "------ Baby Bee ------",
        "ab LongEnough ●",  # "ab" is 2 chars → skipped
    ]
    result = parse_guild_list(lines)
    assert igns(result) == ["LongEnough"]


# ── parse_online_igns ──────────────────────────────────────────────────────

GUILD_ONLINE = [
    "Guild Name: Bumble Kindergarten",
    "Online Members: (2/25)",
    "● [VIP] PlayerBeta ●  [MVP++] PlayerGamma ●",
]

def test_parse_online_basic():
    result = parse_online_igns(GUILD_ONLINE)
    assert result == {"PlayerBeta", "PlayerGamma"}

def test_parse_online_skips_header_lines():
    """Lines with ':' (e.g. 'Online Members: (2/25)') must be ignored."""
    result = parse_online_igns(GUILD_ONLINE)
    assert "Members" not in result
    assert "Online" not in result

def test_parse_online_empty():
    assert parse_online_igns([]) == set()

def test_parse_online_no_one_online():
    lines = [
        "Guild Name: Bumble Kindergarten",
        "Online Members: (0/25)",
    ]
    assert parse_online_igns(lines) == set()

def test_parse_online_returns_set():
    """Result type must be a set (used for O(1) membership checks)."""
    assert isinstance(parse_online_igns(GUILD_ONLINE), set)

def test_parse_online_single_player():
    lines = ["[MVP+] OnlyOne ●"]
    result = parse_online_igns(lines)
    assert result == {"OnlyOne"}
