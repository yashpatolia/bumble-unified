"""Tests for pure utility functions: condense (lib/condense.py) and deep_get (lib/deep_get.py)."""
import pytest
from lib.condense import condense
from lib.deep_get import deep_get


# ── condense ───────────────────────────────────────────────────────────────

class TestCondense:
    def test_zero(self):
        assert condense(0) == "0"

    def test_small_int(self):
        assert condense(999) == "999"

    def test_exactly_one_thousand(self):
        assert condense(1000) == "1K"

    def test_thousands(self):
        assert condense(1500) == "1.5K"

    def test_millions(self):
        assert condense(1_500_000) == "1.5M"

    def test_millions_exact(self):
        assert condense(2_000_000) == "2M"

    def test_billions(self):
        assert condense(1_200_000_000) == "1.2B"

    def test_trillions(self):
        assert condense(5_000_000_000_000) == "5T"

    def test_negative(self):
        result = condense(-1_500_000)
        assert result == "-1.5M"

    def test_string_passthrough(self):
        """If a string is passed in, it should be returned unchanged."""
        assert condense("already a string") == "already a string"

    def test_float_input(self):
        assert condense(1_500_000.0) == "1.5M"

    def test_trailing_zeros_stripped(self):
        """1.0M should render as '1M', not '1.0M'."""
        assert condense(1_000_000) == "1M"

    def test_four_sig_figs(self):
        """condense uses 4 significant figures."""
        assert condense(1_234_567) == "1.235M"


# ── deep_get ───────────────────────────────────────────────────────────────

class TestDeepGet:
    def test_single_key(self):
        assert deep_get({"a": 1}, ["a"]) == 1

    def test_nested_two_levels(self):
        d = {"outer": {"inner": 42}}
        assert deep_get(d, ["outer", "inner"]) == 42

    def test_nested_three_levels(self):
        d = {"a": {"b": {"c": "found"}}}
        assert deep_get(d, ["a", "b", "c"]) == "found"

    def test_missing_key_returns_default(self):
        assert deep_get({"a": 1}, ["b"]) is None

    def test_missing_key_custom_default(self):
        assert deep_get({}, ["missing"], default=0) == 0

    def test_missing_intermediate_key(self):
        d = {"a": {"x": 1}}
        assert deep_get(d, ["a", "b", "c"]) is None

    def test_empty_path(self):
        d = {"a": 1}
        assert deep_get(d, []) == d

    def test_empty_dict(self):
        assert deep_get({}, ["a", "b"]) is None

    def test_none_value_at_leaf(self):
        d = {"a": None}
        assert deep_get(d, ["a"]) is None

    def test_non_dict_intermediate(self):
        """If an intermediate value is not a dict, return the default."""
        d = {"a": "not_a_dict"}
        assert deep_get(d, ["a", "b"]) is None

    def test_list_value_at_leaf(self):
        """deep_get should return a list if it's the final value."""
        d = {"a": [1, 2, 3]}
        assert deep_get(d, ["a"]) == [1, 2, 3]

    def test_real_skyblock_path(self):
        """Mirrors the pattern used in player code for Skyblock API responses."""
        profile = {
            "members": {
                "abc123": {
                    "leveling": {"experience": 12345}
                }
            }
        }
        xp = deep_get(profile, ["members", "abc123", "leveling", "experience"])
        assert xp == 12345

    def test_real_skyblock_path_missing_member(self):
        profile = {"members": {}}
        xp = deep_get(profile, ["members", "abc123", "leveling", "experience"], default=0)
        assert xp == 0
