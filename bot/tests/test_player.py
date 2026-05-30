"""Tests for player subclasses: SkyblockLevel, Catacombs, Slayers, MagicalPower.

All classes are constructed with plain dicts — no API calls, no NBT binary data.
"""
import pytest
from constants import DUNGEON_XP_TABLE

from player.level import SkyblockLevel
from player.catacombs import Catacombs
from player.slayers import Slayers
from player.magical_power import MagicalPower


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_member(
    xp=0,
    cata_xp=0,
    secrets=0,
    tier_completions=None,
    master_completions=None,
    slayer_bosses=None,
):
    """Build a minimal member_data dict shaped like the Hypixel API."""
    return {
        "leveling": {"experience": xp},
        "dungeons": {
            "dungeon_types": {
                "catacombs": {
                    "experience": cata_xp,
                    "tier_completions": tier_completions or {},
                    "fastest_time_s_plus": {},
                    "fastest_time_s": {},
                    "fastest_time": {},
                },
                "master_catacombs": {
                    "tier_completions": master_completions or {},
                    "fastest_time_s_plus": {},
                    "fastest_time_s": {},
                    "fastest_time": {},
                },
            },
            "secrets": secrets,
        },
        "slayer": {"slayer_bosses": slayer_bosses or {}},
    }


# ── SkyblockLevel ─────────────────────────────────────────────────────────────

class TestSkyblockLevel:
    def test_current_level_from_xp(self):
        data = {"leveling": {"experience": 25000}}
        sl = SkyblockLevel(data, [(data, "")])
        assert sl.current == 250.0

    def test_zero_xp_gives_zero(self):
        sl = SkyblockLevel({}, [({}, "")])
        assert sl.current == 0.0

    def test_highest_picks_max_across_profiles(self):
        low = {"leveling": {"experience": 10000}}
        high = {"leveling": {"experience": 50000}}
        sl = SkyblockLevel(low, [(low, ""), (high, " ♻")])
        assert sl.highest == (500.0, " ♻")

    def test_highest_when_selected_is_best(self):
        selected = {"leveling": {"experience": 50000}}
        other = {"leveling": {"experience": 10000}}
        sl = SkyblockLevel(selected, [(selected, ""), (other, "")])
        assert sl.highest == (500.0, "")

    def test_highest_with_no_profiles_returns_zero(self):
        sl = SkyblockLevel({}, [])
        assert sl.highest == (0.0, "")

    def test_current_and_highest_can_differ(self):
        selected = {"leveling": {"experience": 10000}}
        ironman = {"leveling": {"experience": 40000}}
        sl = SkyblockLevel(selected, [(selected, ""), (ironman, " ♻")])
        assert sl.current == 100.0
        assert sl.highest == (400.0, " ♻")


# ── Catacombs ─────────────────────────────────────────────────────────────────

class TestCatacombs:
    def _make(self, cata_xp=0, secrets=0, tier=None, master=None, all_members=None):
        data = make_member(cata_xp=cata_xp, secrets=secrets, tier_completions=tier, master_completions=master)
        return Catacombs(data, all_members or [(data, "")])

    def test_zero_xp_gives_level_zero(self):
        assert self._make(cata_xp=0).level == 0.0

    def test_level_1_at_50_xp(self):
        # DUNGEON_XP_TABLE[1] = 50
        assert self._make(cata_xp=50).level == 1.0

    def test_fractional_level_between_1_and_2(self):
        # DUNGEON_XP_TABLE[1]=50, DUNGEON_INDIVIDUAL_XP_TABLE[2]=75
        # level = 1 + round((87-50)/75, 2) = 1.49
        assert self._make(cata_xp=87).level == pytest.approx(1.49, abs=0.01)

    def test_level_50_exact_boundary(self):
        c = self._make(cata_xp=DUNGEON_XP_TABLE[50])
        assert c.level == 50.0

    def test_past_level_50_gives_fractional_above_50(self):
        # 200M xp past 50 = exactly level 51.0
        c = self._make(cata_xp=DUNGEON_XP_TABLE[50] + 200_000_000)
        assert c.level == pytest.approx(51.0, abs=0.01)

    def test_secrets_returned(self):
        assert self._make(secrets=1234).secrets == 1234

    def test_spr_zero_when_no_runs(self):
        assert self._make(secrets=500).spr == 0.0

    def test_spr_calculation(self):
        # tier_completions: total key is subtracted; floor keys are summed
        tier = {"total": 10, "0": 3, "1": 7}  # 10 actual runs, 100 secrets → 10.0 spr
        assert self._make(secrets=100, tier=tier).spr == pytest.approx(10.0, abs=0.01)

    def test_spr_combines_normal_and_master(self):
        tier = {"total": 5, "7": 5}       # 5 normal runs
        master = {"total": 5, "1": 5}     # 5 master runs → 10 total, 200 secrets → 20.0 spr
        assert self._make(secrets=200, tier=tier, master=master).spr == pytest.approx(20.0, abs=0.01)

    def test_pb_no_data_returns_none_strings(self):
        s_plus, s, comp, ctype = self._make().pb("f", "7")
        assert s_plus == "None"
        assert s == "None"
        assert comp == "None"
        assert ctype == "Catacombs"

    def test_pb_master_mode_label(self):
        _, _, _, ctype = self._make().pb("m", "1")
        assert ctype == "Master Catacombs"

    def test_pb_formats_milliseconds(self):
        data = make_member()
        data["dungeons"]["dungeon_types"]["catacombs"]["fastest_time_s_plus"] = {"7": 120_000}
        c = Catacombs(data, [(data, "")])
        s_plus, _, _, _ = c.pb("f", "7")
        assert s_plus == "2:00"

    def test_pb_picks_best_time_across_profiles(self):
        slow = make_member()
        slow["dungeons"]["dungeon_types"]["catacombs"]["fastest_time_s_plus"] = {"7": 200_000}
        fast = make_member()
        fast["dungeons"]["dungeon_types"]["catacombs"]["fastest_time_s_plus"] = {"7": 120_000}
        c = Catacombs(slow, [(slow, ""), (fast, "")])
        s_plus, _, _, _ = c.pb("f", "7")
        assert s_plus == "2:00"


# ── Slayers ───────────────────────────────────────────────────────────────────

class TestSlayers:
    def test_empty_profile_all_zeros(self):
        assert Slayers({}).levels == "0/0/0/0/0/0"

    def test_partial_slayers(self):
        data = make_member(slayer_bosses={
            "zombie": {"claimed_levels": {"level_1": True, "level_2": True}},
            "spider": {"claimed_levels": {"level_1": True}},
        })
        assert Slayers(data).levels == "2/1/0/0/0/0"

    def test_zombie_capped_at_9(self):
        levels = {f"level_{i}": True for i in range(1, 12)}  # 11 entries
        data = make_member(slayer_bosses={"zombie": {"claimed_levels": levels}})
        assert Slayers(data).levels.startswith("9/")

    def test_all_bosses_populated(self):
        bosses = {
            name: {"claimed_levels": {f"l{i}": True for i in range(5)}}
            for name in ("zombie", "spider", "wolf", "enderman", "blaze", "vampire")
        }
        data = make_member(slayer_bosses=bosses)
        assert Slayers(data).levels == "5/5/5/5/5/5"


# ── MagicalPower ──────────────────────────────────────────────────────────────

class TestMagicalPower:
    def test_no_member_data_returns_zeros(self):
        mp = MagicalPower({})
        assert mp.total == 0
        assert mp.highest == 0

    def test_missing_talisman_bag_returns_zeros(self):
        data = {"inventory": {"bag_contents": {}}}
        mp = MagicalPower(data)
        assert mp.total == 0
        assert mp.highest == 0

    def test_null_talisman_bag_returns_zeros(self):
        data = {"inventory": {"bag_contents": {"talisman_bag": {"data": None}}}}
        mp = MagicalPower(data)
        assert mp.total == 0
        assert mp.highest == 0
