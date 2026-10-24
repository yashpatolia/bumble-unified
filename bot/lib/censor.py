import os
import re

# Words masked in chat shown on the web panel. Whole words only (so "class" or
# "Scunthorpe" are untouched), tolerant of simple obfuscation: leetspeak
# (f@ck, sh1t), stretched letters (fuuuck) and common suffixes (fucking, bitches).
# Add more without a code change via CHAT_CENSOR_WORDS="word1,word2".
_BASE_WORDS = [
    "fuck", "shit", "bitch", "asshole", "bastard", "cunt", "dick", "cock", "piss",
    "slut", "whore", "wanker", "twat", "prick",
    "nigger", "nigga", "faggot", "fag", "retard", "tranny", "dyke", "chink", "spic", "kike", "coon",
]

_LEET = {"a": "a@4", "e": "e3", "i": "i1!", "o": "o0", "s": "s$5", "t": "t7", "l": "l1"}
_SUFFIX = r"(?:s|es|ed|ing|in|er|ers|y)?"


def _char_class(ch: str) -> str:
    return "[" + "".join(re.escape(c) for c in _LEET.get(ch, ch)) + "]+"


def _build_pattern() -> re.Pattern:
    extra = [w.strip().lower() for w in os.getenv("CHAT_CENSOR_WORDS", "").split(",") if w.strip()]
    words = sorted(set(_BASE_WORDS + extra), key=len, reverse=True)
    alternatives = ["".join(_char_class(c) for c in w) for w in words]
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(alternatives) + r")" + _SUFFIX + r"(?![A-Za-z0-9])", re.IGNORECASE)


_PATTERN = _build_pattern()


def censor(text: str) -> str:
    """Replace each blocked word with asterisks of the same length."""
    return _PATTERN.sub(lambda m: "*" * len(m.group(0)), text)
