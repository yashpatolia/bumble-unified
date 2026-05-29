import re

_RANK_HEADER = re.compile(r"^-+\s+(.+?)\s+-+$")
_SKIP_WORDS = {"Guild", "Total", "Online", "Members", "The"}


def parse_guild_list(lines: list) -> list:
    """Parse /guild list output into [{"ign": str, "rank": str}, ...]."""
    members = []
    current_rank = ""
    for line in lines:
        line = line.strip()
        if not line or ":" in line:
            continue
        m = _RANK_HEADER.match(line)
        if m:
            current_rank = m.group(1).strip()
            continue
        clean = re.sub(r"\[[\w+]+\]", "", line).replace("●", "").replace("•", "")
        for token in clean.split():
            if re.match(r"^[A-Za-z0-9_]{3,16}$", token) and token not in _SKIP_WORDS:
                members.append({"ign": token, "rank": current_rank})
    return members


def parse_online_igns(lines: list) -> set:
    """Parse /guild online output into a set of online IGNs."""
    online = set()
    for line in lines:
        line = line.strip()
        if not line or ":" in line or "--" in line:
            continue
        clean = re.sub(r"\[[\w+]+\]", "", line).replace("●", "").replace("•", "")
        for token in clean.split():
            if re.match(r"^[A-Za-z0-9_]{3,16}$", token) and token not in _SKIP_WORDS:
                online.add(token)
    return online
