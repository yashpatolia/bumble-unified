"""Chimera boss drop-rate math. Pure formula, no Hypixel API call — takes the
looting level and magic find the player supplies via `.chim` directly."""


def chim_drop_rates(looting: int, magic_find: int) -> dict:
    """Returns {"legendary": %, "mythic": %} drop chances for the given
    looting enchant level and magic find stat."""
    multiplier = (1 + looting * 0.15) * (1 + magic_find / 100)
    return {
        "legendary": 1 * multiplier,
        "mythic": 1.25 * multiplier,
    }
