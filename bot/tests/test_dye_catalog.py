"""Consistency checks between the dye seed migration and constants.py's
DYE_ROLES / DYE_EMOJIS maps. Catches drift if either is edited without the other.
"""
import re
from pathlib import Path

import pytest

from constants import DYE_ROLES, DYE_EMOJIS

_MIGRATION = Path(__file__).parent.parent / "db" / "migrations" / "015_dye_catalog.sql"
_ROW_RE = re.compile(r"\('(?P<dye_id>\w+)',\s*'(?P<dye_name>[^']+)',\s*(?P<weight>[^,]+),\s*'(?P<hex>[0-9A-Fa-f]{6})'\)")


def _seeded_dyes() -> dict:
    text = _MIGRATION.read_text()
    return {m["dye_id"]: m for m in _ROW_RE.finditer(text)}


@pytest.fixture(scope="module")
def seeded():
    return _seeded_dyes()


def test_migration_file_exists():
    assert _MIGRATION.exists()


def test_seed_includes_nothing_bucket(seeded):
    assert "nothing" in seeded
    assert seeded["nothing"]["hex"].upper() == "000000"


def test_every_dye_role_is_seeded(seeded):
    """Every dye_id with a Discord role must have a matching seeded catalog row."""
    missing = set(DYE_ROLES) - set(seeded)
    assert not missing, f"DYE_ROLES entries missing from dye seed migration: {missing}"


def test_every_dye_emoji_is_seeded(seeded):
    missing = set(DYE_EMOJIS) - set(seeded)
    assert not missing, f"DYE_EMOJIS entries missing from dye seed migration: {missing}"


def test_no_extra_seeded_dyes(seeded):
    """Every real (non-'nothing') seeded dye should have a role, or it can never be equipped."""
    extra = (set(seeded) - {"nothing"}) - set(DYE_ROLES)
    assert not extra, f"Seeded dyes with no Discord role in DYE_ROLES: {extra}"


def test_seeded_hex_codes_are_valid(seeded):
    hex_re = re.compile(r"^[0-9A-Fa-f]{6}$")
    for dye_id, row in seeded.items():
        assert hex_re.match(row["hex"]), f"{dye_id} has an invalid hex code: {row['hex']}"


def test_no_duplicate_dye_ids():
    text = _MIGRATION.read_text()
    all_ids = re.findall(r"\('(\w+)',", text)
    assert len(all_ids) == len(set(all_ids)), "Duplicate dye_id rows in the seed migration"


def test_weights_are_positive(seeded):
    for dye_id, row in seeded.items():
        weight = float(row["weight"])
        assert weight > 0, f"{dye_id} has a non-positive weight"


def test_nothing_dominates_the_pool(seeded):
    """'nothing' must have the largest weight so most rolls result in no drop."""
    nothing_weight = float(seeded["nothing"]["weight"])
    for dye_id, row in seeded.items():
        if dye_id == "nothing":
            continue
        assert float(row["weight"]) < nothing_weight
