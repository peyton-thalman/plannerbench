"""Tests for the clean-room engine.

Run:  python3 -I -m unittest discover -s checks/cleanroom

Every worked mini-example of RULES.md Section 16, using the parameter values each example states (illustrative
values are injected through Params overrides), plus boundary tests named in the build brief.
"""

import copy
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine as E  # noqa: E402
import params as P  # noqa: E402
from params import Params  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def single_household(born, accounts, actions=None, first=2026, last=2027, ret=0.0, people_extra=None,
                     spending=0.0, state="none"):
    person = {"id": "p", "born": born, "born_month": 1, "medicare": False}
    person.update(people_extra or {})
    return {
        "household": {"filing": "single", "state": state, "people": [person], "accounts": accounts,
                      "income": [], "spending_need": spending,
                      "itemized": {"salt_other": 0, "mortgage_interest": 0, "medical": 0, "charity_cash": 0}},
        "plans": [{"name": "A", "actions": actions or []}],
        "events": [],
        "assumptions": {"return": ret, "inflation": 0.0, "first_year": first, "last_year": last,
                        "heirs_tax_rate": 0.0, "switches": {}},
    }


def row(out, year, plan="A"):
    return next(r for r in out["plans"][plan]["years"] if r["year"] == year)


# ---------------------------------------------------------------------------------------------------------
# Section 16 worked examples
# ---------------------------------------------------------------------------------------------------------
class Example1ProRata(unittest.TestCase):
    """16 Example 1: Form 8606 pro-rata with basis over two years; the 401(k) stays out of line 6."""

    def test_form_lines(self):
        y1 = E.form8606(20000, 70000, 0, 30000)
        self.assertAlmostEqual(y1["line9"], 100000)
        self.assertAlmostEqual(y1["line10"], 0.2)
        self.assertAlmostEqual(y1["line11"], 6000)
        self.assertAlmostEqual(y1["line18"], 24000)
        self.assertAlmostEqual(y1["line14"], 14000)
        y2 = E.form8606(y1["line14"], 40000, 0, 30000)
        self.assertAlmostEqual(y2["line9"], 70000)
        self.assertAlmostEqual(y2["line10"], 0.2)
        self.assertAlmostEqual(y2["line11"], 6000)
        self.assertAlmostEqual(y2["line18"], 24000)
        self.assertAlmostEqual(y2["line14"], 8000)
        rolled = E.form8606(20000, 270000, 0, 30000)   # had the 401(k) been an IRA on Dec 31
        self.assertAlmostEqual(rolled["line11"], 2000)

    def test_engine_two_years(self):
        raw = single_household(1966, [
            {"id": "A", "owner": "p", "type": "traditional_ira", "balance": 90000, "after_tax_basis": 20000},
            {"id": "B", "owner": "p", "type": "traditional_ira", "balance": 10000},
            {"id": "K", "owner": "p", "type": "401k", "balance": 200000},
            {"id": "C", "owner": "p", "type": "cash", "balance": 100000},
        ], actions=[{"type": "roth_conversion", "from": "A", "amount": 30000, "years": [2026, 2027]}])
        out = E.run(raw)
        r1, r2 = row(out, 2026), row(out, 2027)
        self.assertEqual(r1["conversion"]["A"], 30000)
        self.assertEqual(r1["income"]["ira_taxable"], 24000)
        self.assertEqual(r1["basis8606"]["p"], 14000)
        self.assertEqual(r1["balances"]["A"], 60000)
        self.assertEqual(r2["income"]["ira_taxable"], 24000)
        self.assertEqual(r2["basis8606"]["p"], 8000)
        self.assertEqual(r2["balances"]["K"], 200000)
        self.assertEqual(r1["additional_10pct"], 0)       # no 10% on a conversion (7.4)


class Example2RmdQcdConversion(unittest.TestCase):
    """16 Example 2: RMD first, the QCD counts toward it, then the conversion."""

    def scenario(self, convert):
        return single_household(1951, [
            {"id": "ira", "owner": "p", "type": "traditional_ira", "balance": 265000},
            {"id": "cash", "owner": "p", "type": "cash", "balance": 50000},
        ], actions=[{"type": "qcd", "from": "ira", "amount": 4000, "years": [2026]},
                    {"type": "roth_conversion", "from": "ira", "amount": convert, "years": [2026]}],
            ret=0.05, last=2026)

    def test_example(self):
        r = row(E.run(self.scenario(50000)), 2026)
        self.assertEqual(r["rmd"]["ira"], 10772.36)
        self.assertEqual(r["qcd"]["ira"], 4000)
        self.assertEqual(r["conversion"]["ira"], 50000)
        self.assertEqual(r["balances"]["ira"], 217477.64)
        self.assertEqual(r["distributions"]["ira"], 60772.36)       # Form 1040 line 4a
        self.assertEqual(r["income"]["ira_taxable"], 56772.36)      # line 4b, QCD excluded
        self.assertNotIn("action_clamped", r["flags"])

    def test_clamped_conversion(self):
        r = row(E.run(self.scenario(278250)), 2026)
        self.assertEqual(r["conversion"]["ira"], 267477.64)
        self.assertEqual(r["balances"]["ira"], 0)
        self.assertIn("action_clamped", r["flags"])


class Example3InheritedAfterRbd(unittest.TestCase):
    """16 Example 3: designated beneficiary, owner died after the RBD, minus-one method."""

    def setup_sched(self, reached=None):
        inh = {"from_born": 1945, "died": 2022, "beneficiary_class": "designated"}
        if reached is not None:
            inh["owner_had_reached_rbd"] = reached
        acc = {"type": "inherited_ira", "inherited": inh}
        return E.inherited_setup(acc, {"born": 1975}, E.default_switches("single", "none"))

    def test_divisor_and_rmd(self):
        s = self.setup_sched()
        self.assertTrue(s["rbd"])                                    # derived: died 2022 >= RBD year 2016
        prm = Params()
        self.assertAlmostEqual(E.inherited_rmd(s, 2026, 351000, 351000 * 1.05, prm), 10000.00, places=6)
        # 2023 divisor 38.1 (beneficiary) beats 12.3 (owner); 2023 and 2024 waived anyway
        self.assertEqual(E.inherited_rmd(s, 2023, 351000, 351000, prm), 0.0)
        self.assertEqual(E.inherited_rmd(s, 2024, 351000, 351000, prm), 0.0)
        self.assertAlmostEqual(E.inherited_rmd(s, 2025, 361000, 361000, prm), 361000 / 36.1)
        self.assertEqual(E.inherited_rmd(s, 2032, 100000, 105000, prm), 105000)   # D+10: everything

    def test_before_rbd_contrast(self):
        s = self.setup_sched(reached=False)
        prm = Params()
        self.assertEqual(E.inherited_rmd(s, 2026, 351000, 351000, prm), 0.0)
        self.assertEqual(E.inherited_rmd(s, 2032, 100000, 105000, prm), 105000)

    def test_no_10pct_on_inherited(self):
        raw = single_household(1990, [
            {"id": "inh", "owner": "p", "type": "inherited_ira", "balance": 100000,
             "inherited": {"from_born": 1945, "died": 2022, "beneficiary_class": "designated"}},
        ], actions=[{"type": "withdrawal", "from": "inh", "amount": 20000, "years": [2026]}], last=2026)
        r = row(E.run(raw), 2026)
        self.assertEqual(r["additional_10pct"], 0)


class Example4Torpedo(unittest.TestCase):
    """16 Example 4: Social Security 'torpedo' (statutory base amounts, illustrative 12% bracket)."""

    def test_torpedo(self):
        prm = Params()
        self.assertAlmostEqual(E.taxable_social_security(40000, 30000, 0, "mfj", prm), 11100)
        self.assertAlmostEqual(E.taxable_social_security(40000, 31000, 0, "mfj", prm), 11950)
        flat12 = [(None, 0.12)]
        ti = 50000.0
        extra = E.ordinary_tax(ti + 1000 + 850, flat12) - E.ordinary_tax(ti, flat12)
        self.assertAlmostEqual(extra, 222)


class Example5SeniorDeduction(unittest.TestCase):
    """16 Example 5: the phase-out comes off each person's amount."""

    def test_per_person(self):
        prm = Params()
        self.assertAlmostEqual(E.senior_deduction(2026, 170000, 2, "mfj", prm), 9600)
        self.assertAlmostEqual(E.senior_deduction(2026, 170000, 1, "mfj", prm), 4800)
        self.assertAlmostEqual(E.senior_deduction(2026, 250000, 2, "mfj", prm), 0)
        self.assertAlmostEqual(E.senior_deduction(2026, 250000, 1, "mfj", prm), 0)
        self.assertAlmostEqual(E.senior_deduction(2026, 249000, 2, "mfj", prm), 2 * 60)   # 0.12 per dollar
        self.assertAlmostEqual(E.senior_deduction(2029, 100000, 2, "mfj", prm), 0)       # expired
        self.assertAlmostEqual(E.senior_deduction(2028, 75000, 1, "single", prm), 6000)
        self.assertAlmostEqual(E.senior_deduction(2028, 175000, 1, "single", prm), 0)


class Example6ZeroBand(unittest.TestCase):
    """16 Example 6: 0% gains pushed into 15% (illustrative thresholds and a flat 12% bracket)."""

    def test_example(self):
        flat12 = [(None, 0.12)]
        before, lb = E.qdcg_tax(110000, 0, 30000, flat12, 100000, 600000, 0.15, 0.20)
        self.assertAlmostEqual(lb["L9"], 20000)
        self.assertAlmostEqual(lb["L17"], 10000)
        self.assertAlmostEqual(before, 9600 + 1500)
        after, la = E.qdcg_tax(120000, 0, 30000, flat12, 100000, 600000, 0.15, 0.20)
        self.assertAlmostEqual(la["L9"], 10000)
        self.assertAlmostEqual(la["L17"], 20000)
        self.assertAlmostEqual(after - before, 2700)

    def test_engine_level_with_injected_params(self):
        prm = Params(overrides={"ordinary_brackets": {"mfj": [(None, 0.12)], "single": [(None, 0.12)]},
                                "cg_thresholds": {"mfj": {"zero_max": 100000, "fifteen_max": 600000},
                                                  "single": {"zero_max": 100000, "fifteen_max": 600000}}})
        self.assertAlmostEqual(E.regular_tax(2026, "mfj", 110000, 0, 30000, prm), 11100)
        self.assertAlmostEqual(E.regular_tax(2026, "mfj", 120000, 0, 30000, prm), 13800)


class Example7IrmaaLookback(unittest.TestCase):
    """16 Example 7: two-year lookback uses the filing status of the earlier return."""

    single = [100000, 125000, 160000, 200000, 500000]
    joint = [200000, 250000, 320000, 400000, 750000]

    def tier(self, magi, filing):
        return E.irmaa_tier(magi, self.single if filing == "single" else self.joint)

    def test_table(self):
        returns = {2025: (210000, "mfj"), 2026: (230000, "mfj"), 2027: (120000, "single")}
        prior = {2024: {"magi": 150000, "filing": "mfj"}}
        expect = {2027: (2025, "mfj", 1), 2028: (2026, "mfj", 1), 2029: (2027, "single", 1)}
        for prem_year, (L, filing, tier) in expect.items():
            magi, f, look, assumed = E.irmaa_lookup(prem_year, returns, prior, 2025, 2)
            self.assertEqual((look, f, assumed), (L, filing, False))
            self.assertEqual(self.tier(magi, f), tier)
        # 2026 premiums use the 2024 return (before first_year: prior_magi)
        magi, f, look, assumed = E.irmaa_lookup(2026, returns, prior, 2025, 2)
        self.assertEqual((magi, f, look), (150000, "mfj", 2024))
        # wrongly using the single table with 230,000 lands above tier 2
        self.assertGreater(self.tier(230000, "single"), 2)
        # boundary: exactly 200,000 joint is tier 0
        self.assertEqual(self.tier(200000, "mfj"), 0)
        # SSA-44 alternative for 2027/2028 from the 2027 single return: tier 1 (reported, not applied)
        self.assertEqual(self.tier(120000, "single"), 1)

    def test_missing_prior_is_assumed_tier0(self):
        magi, f, look, assumed = E.irmaa_lookup(2026, {}, {}, 2026, 2)
        self.assertTrue(assumed)
        self.assertEqual(look, 2024)


class Example8Survivor(unittest.TestCase):
    """16 Example 8: survivor benefit and the widow's limit (COLA 0)."""

    def scenario(self, d_born, d_claim, s_born, s_pia, s_claim, death, first, last):
        return {
            "household": {
                "filing": "mfj", "state": "none",
                "people": [
                    {"id": "d", "born": d_born, "born_month": 1, "medicare": False,
                     "social_security": {"monthly_at_fra": 2000, "claim_age": d_claim}},
                    {"id": "s", "born": s_born, "born_month": 1, "medicare": False,
                     "social_security": {"monthly_at_fra": s_pia, "claim_age": s_claim}},
                ],
                "accounts": [{"id": "cash", "owner": "joint", "type": "cash", "balance": 1000000}],
                "income": [], "spending_need": 0,
                "itemized": {"salt_other": 0, "mortgage_interest": 0, "medical": 0, "charity_cash": 0}},
            "plans": [{"name": "A", "actions": []}],
            "events": [{"type": "death", "person": "d", "year": death}],
            "assumptions": {"return": 0.0, "inflation": 0.0, "cola": 0.0, "first_year": first, "last_year": last,
                            "heirs_tax_rate": 0.0, "switches": {}},
        }

    def run0(self, raw):
        prm = Params(inflation=0.0, cola=0.0, overrides={"ss_cola": 0.0})
        return E.run(raw, prm)

    def test_claimed_at_62_widow_limit(self):
        # S born 1958: survivor FRA 66y4m = 796 months; own 1,200 claimed at that age.
        out = self.run0(self.scenario(1960, 62, 1958, 1200, 796 / 12, 2030, 2026, 2031))
        self.assertEqual(row(out, 2030)["social_security"]["d"], 1400 * 12)   # 30% early reduction
        self.assertEqual(row(out, 2031)["social_security"]["s"], 1650 * 12)   # RIB-LIM 82.5% binds

    def test_claimed_at_70(self):
        out = self.run0(self.scenario(1960, 70, 1958, 1200, 796 / 12, 2030, 2026, 2031))
        self.assertEqual(row(out, 2030)["social_security"]["d"], 2480 * 12)
        self.assertEqual(row(out, 2031)["social_security"]["s"], 2480 * 12)

    def test_survivor_at_62(self):
        # S born 1964 (survivor FRA 67): survivor benefit from Jan 2026 at age 62, 60 months early.
        out = self.run0(self.scenario(1960, 62, 1964, 500, 67, 2025, 2025, 2026))
        self.assertEqual(row(out, 2026)["social_security"]["s"], 1592 * 12)


    def test_v12_already_claimed_ratio_keeps_drcs(self):
        # v1.2: no claimed_at_months -> factor = 2480 / 2000 = 1.24, so the survivor base keeps the credits.
        raw = self.scenario(1960, 70, 1958, 1200, 796 / 12, 2026, 2026, 2027)
        raw["household"]["people"][0]["social_security"] = {"monthly_at_fra": 2000, "already_claimed_monthly": 2480}
        out = self.run0(raw)
        self.assertEqual(row(out, 2027)["social_security"]["s"], 2480 * 12)

    def test_v12_unclaimed_death_credits_through_november(self):
        # d born Jan 1960 (FRA 804 months) dies in 2028 before claiming. November 2028 = 826 months:
        # 22 months of credits -> 2,000 x 1.14667 = 2,293.33 -> 2,293.30 -> paid 2,293 (December would give 2,306).
        out = self.run0(self.scenario(1960, 70, 1958, 1200, 796 / 12, 2028, 2026, 2029))
        self.assertEqual(row(out, 2029)["social_security"]["s"], 2293 * 12)


class SuccessorAndStepUpV12(unittest.TestCase):
    """3.3 step 4/6A.6 successor deadline and 3.3 step 5 joint-account step-up, as amended in v1.2."""

    def death(self, accounts, switches=None):
        sc = {"switches": dict(E.default_switches("mfj", "AZ"), **(switches or {})), "deaths": {"d": 2030}}
        st = {"acc": {a["id"]: a for a in accounts}, "order": [a["id"] for a in accounts],
              "basis8606": {"d": 0.0, "s": 0.0}, "deferred": {},
              "roth": {"d": {"first": None, "contrib": 0.0, "layers": []},
                       "s": {"first": None, "contrib": 0.0, "layers": []}}}
        flags = E.apply_death(st, sc, "d", "s")
        return st, flags

    def inherited(self, cls, reached):
        acc = {"type": "inherited_ira", "inherited": {"from_born": 1945, "died": 2022,
                                                      "beneficiary_class": cls, "owner_had_reached_rbd": reached}}
        sched = E.inherited_setup(acc, {"born": 1975}, E.default_switches("mfj", "none"))
        return {"id": cls, "owner": "d", "type": "inherited_ira", "bal": 1000.0, "basis": 0.0, "sched": sched}

    def test_successor_deadlines(self):
        accs = [self.inherited("designated", True), self.inherited("disabled", False),
                self.inherited("non_designated", True), self.inherited("minor_child", False)]
        st, _ = self.death(accs)
        self.assertEqual(st["acc"]["designated"]["sched"]["deadline"], 2032)      # keeps D + 10
        self.assertEqual(st["acc"]["disabled"]["sched"]["deadline"], 2040)        # EDB: D_b + 10
        self.assertIsNone(st["acc"]["non_designated"]["sched"]["deadline"])       # owner LE: no limit
        self.assertEqual(st["acc"]["minor_child"]["sched"]["deadline"], 2006)     # min(1975+21+10, 2040)

    def taxable(self, titling):
        return {"id": "t", "owner": "joint", "type": "taxable", "bal": 100000.0, "basis": 40000.0,
                "titling": titling}

    def test_joint_titling(self):
        for titling, basis, flagged in [("community", 100000, False), ("community_with_survivorship", 100000, False),
                                        ("jtwros", 70000, False), (None, 70000, True)]:
            st, flags = self.death([self.taxable(titling)])
            self.assertAlmostEqual(st["acc"]["t"]["basis"], basis, msg=titling)
            self.assertEqual("stepup_titling_assumed" in flags, flagged, titling)
            self.assertEqual(st["acc"]["t"]["owner"], "s")
        st, flags = self.death([self.taxable(None)], {"community_property": True})
        self.assertAlmostEqual(st["acc"]["t"]["basis"], 100000)

    def test_switch_default_false_in_az(self):
        self.assertFalse(E.default_switches("mfj", "AZ")["community_property"])


class ArizonaStandardDeductionV12(unittest.TestCase):
    def test_equals_federal_basic(self):
        prm = Params(inflation=0.03)
        self.assertEqual(prm.get("az_standard_deduction", 2025), {"mfj": 31500, "single": 15750})
        self.assertEqual(prm.projected_years, set())
        self.assertEqual(prm.get("az_standard_deduction", 2026), {"mfj": 32200, "single": 16100})
        self.assertEqual(prm.projected_years, {2026})                 # labelled projected until ADOR publishes
        self.assertEqual(prm.get("az_standard_deduction", 2027), prm.get("standard_deduction", 2027))


class Example9Section68(unittest.TestCase):
    def test_example(self):
        red = E.itemized_limit_reduction(60000, 1000000, 750000, 2 / 37)
        self.assertAlmostEqual(red, 3243.24, places=2)
        self.assertAlmostEqual(60000 - red, 56756.76, places=2)


class Example10SaltPhaseDown(unittest.TestCase):
    def test_example(self):
        prm = Params()
        self.assertAlmostEqual(E.salt_cap_amount(2026, 600000, prm), 11900)
        self.assertAlmostEqual(min(35000, E.salt_cap_amount(2026, 600000, prm)), 11900)
        self.assertAlmostEqual(E.salt_cap_amount(2026, 610000, prm), 10000)
        self.assertAlmostEqual(E.salt_cap_amount(2030, 600000, prm), 10000)
        self.assertAlmostEqual(E.salt_cap_amount(2030, 100000, prm), 10000)
        self.assertAlmostEqual(E.salt_cap_amount(2027, 0, prm), 40804)


# ---------------------------------------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------------------------------------
class IrmaaBoundaries(unittest.TestCase):
    """12.3: tiers 0-3 upper bounds inclusive, tier 4 upper exclusive, top tier lower bound inclusive."""

    def test_2026_single(self):
        b = Params().get("irmaa_bounds", 2026)["single"]
        self.assertEqual(b, [109000, 137000, 171000, 205000, 500000])
        cases = [(109000, 0), (109000.01, 1), (137000, 1), (137000.01, 2), (171000, 2), (171000.01, 3),
                 (205000, 3), (205000.01, 4), (499999.99, 4), (500000, 5), (2e6, 5), (0, 0)]
        for magi, tier in cases:
            self.assertEqual(E.irmaa_tier(magi, b), tier, magi)

    def test_2026_joint(self):
        b = Params().get("irmaa_bounds", 2026)["mfj"]
        self.assertEqual(b, [218000, 274000, 342000, 410000, 750000])
        cases = [(218000, 0), (218000.01, 1), (274000, 1), (274000.01, 2), (342000, 2), (342000.01, 3),
                 (410000, 3), (410000.01, 4), (749999.99, 4), (750000, 5)]
        for magi, tier in cases:
            self.assertEqual(E.irmaa_tier(magi, b), tier, magi)

    def test_2026_premiums(self):
        prm = Params()
        self.assertEqual(prm.get("part_b_monthly", 2026), [202.9, 284.1, 405.8, 527.5, 649.2, 689.9])
        self.assertEqual(prm.get("part_d_irmaa_monthly", 2026), [0.0, 14.5, 37.5, 60.4, 83.3, 91.0])

    def test_top_frozen_through_2027(self):
        prm = Params(inflation=0.03)
        self.assertEqual(prm.get("irmaa_bounds", 2027)["single"][4], 500000)
        self.assertEqual(prm.get("irmaa_bounds", 2028)["single"][4], 515000)
        self.assertEqual(prm.get("irmaa_bounds", 2028)["mfj"][4], 773000)   # 772,500 rounds half up


class RmdStartAges(unittest.TestCase):
    """6.1 applicable age by birth date, including the 1959 reading (73)."""

    def test_ages(self):
        cases = [((1948, 12), 70.5), ((1949, 6), 70.5), ((1949, 7), 72), ((1950, 12), 72), ((1951, 1), 73),
                 ((1955, 6), 73), ((1959, 1), 73), ((1959, 12), 73), ((1960, 1), 75), ((1965, 6), 75)]
        for (born, month), aa in cases:
            self.assertEqual(P.rmd_applicable_age(born, month), aa, (born, month))

    def test_first_rmd_year(self):
        self.assertEqual(E.first_rmd_year(1949, 6), 2019)    # 70.5 in December 2019
        self.assertEqual(E.first_rmd_year(1948, 8), 2019)    # 70.5 in February 2019
        self.assertEqual(E.first_rmd_year(1949, 7), 2021)
        self.assertEqual(E.first_rmd_year(1951, 3), 2024)
        self.assertEqual(E.first_rmd_year(1959, 3), 2032)
        self.assertEqual(E.first_rmd_year(1960, 3), 2035)

    def test_engine_1959_owner(self):
        raw = single_household(1959, [
            {"id": "ira", "owner": "p", "type": "traditional_ira", "balance": 100000},
            {"id": "cash", "owner": "p", "type": "cash", "balance": 100000},
        ], first=2031, last=2032)
        out = E.run(raw)
        self.assertEqual(row(out, 2031)["rmd"]["ira"], 0)
        self.assertEqual(row(out, 2032)["rmd"]["ira"], round(100000 / 26.5, 2))

    def test_joint_life_divisor(self):
        sc = E.normalize({
            "household": {"filing": "mfj", "state": "none", "people": [
                {"id": "a", "born": 1951}, {"id": "b", "born": 1966}], "accounts": [], "income": []},
            "plans": [], "events": [],
            "assumptions": {"first_year": 2026, "last_year": 2026}})
        acc = {"owner": "a", "type": "traditional_ira"}
        # owner 75, spouse 60: Joint and Last Survivor table (28.3) instead of Uniform (24.6)
        self.assertAlmostEqual(E.owner_rmd(sc, acc, 2026, 283000, 1e9), 283000 / 28.3)


class ZeroBand(unittest.TestCase):
    """The 0% capital-gain band with published 2026 MFJ thresholds (zero_max 98,900)."""

    def test_all_gain_inside_band(self):
        prm = Params()
        self.assertAlmostEqual(E.regular_tax(2026, "mfj", 98900, 0, 98900, prm), 0)
        self.assertAlmostEqual(E.regular_tax(2026, "mfj", 98901, 0, 98901, prm), 0.15)
        self.assertAlmostEqual(E.regular_tax(2026, "mfj", 98900, 98900, 0, prm), 0)   # qualified dividends too

    def test_ordinary_income_fills_band_first(self):
        prm = Params()
        brackets = prm.get("ordinary_brackets", 2026)["mfj"]
        tax = E.regular_tax(2026, "mfj", 100000, 0, 50000, prm)
        self.assertAlmostEqual(tax, E.ordinary_tax(50000, brackets) + 0.15 * (100000 - 98900))


class NoActionPlan(unittest.TestCase):
    def test_identical_to_baseline(self):
        with open(os.path.join(HERE, "sample.json")) as f:
            raw = json.load(f)
        raw = copy.deepcopy(raw)
        raw["plans"] = [{"name": "A", "actions": []},
                        {"name": "Z", "actions": []},
                        {"name": "Never", "actions": [
                            {"type": "roth_conversion", "from": "ira1", "amount": 50000, "years": [2099]},
                            {"type": "qcd", "from": "ira1", "amount": 5000, "years": [1999]}]}]
        out = E.run(raw)
        self.assertEqual(out["plans"]["A"], out["plans"]["Z"])
        self.assertEqual(out["plans"]["A"], out["plans"]["Never"])


class RothOrdering(unittest.TestCase):
    """7.5: contributions, then conversion layers (taxable part first, 5-year penalty clock), then earnings."""

    def test_under_59h(self):
        raw = single_household(1970, [
            {"id": "r", "owner": "p", "type": "roth_ira", "balance": 50000, "first_roth_year": 2020,
             "contribution_basis": 10000,
             "conversion_layers": [{"year": 2024, "taxable_amount": 20000, "nontaxable_amount": 0}]},
            {"id": "cash", "owner": "p", "type": "cash", "balance": 100000},
        ], actions=[{"type": "withdrawal", "from": "r", "amount": 35000, "years": [2026]}], last=2026)
        r = row(E.run(raw), 2026)
        self.assertEqual(r["income"]["ira_taxable"], 5000)          # only earnings are taxed
        self.assertEqual(r["additional_10pct"], 2500)               # 10% of (20,000 layer + 5,000 earnings)


    def test_same_year_conversion_counts(self):
        """7.5 v1.1 (Reg. §1.408A-6 Q&A-9(a), (c)): over 59½ but inside the 5-year clock, a withdrawal in the
        year of a conversion comes out of that year's conversion layer, not earnings."""
        raw = single_household(1960, [
            {"id": "ira", "owner": "p", "type": "traditional_ira", "balance": 100000},
            {"id": "r", "owner": "p", "type": "roth_ira", "balance": 50000, "first_roth_year": 2024},
            {"id": "cash", "owner": "p", "type": "cash", "balance": 100000},
        ], actions=[{"type": "roth_conversion", "from": "ira", "amount": 30000, "years": [2026]},
                    {"type": "withdrawal", "from": "r", "amount": 20000, "years": [2026]}], last=2026)
        r = row(E.run(raw), 2026)
        self.assertEqual(r["income"]["ira_taxable"], 30000)         # the conversion only; no Roth earnings
        self.assertEqual(r["additional_10pct"], 0)


class SaltThresholdSchedule(unittest.TestCase):
    """IRC §164(b)(7)(B)(ii)(III): threshold is 101% of the prior year's for 2027-2029 (federal.json corrected)."""

    def test_thresholds(self):
        prm = Params()
        self.assertAlmostEqual(prm.get("salt", 2027)["threshold"], 510050)
        self.assertAlmostEqual(prm.get("salt", 2028)["threshold"], 515150.50)
        self.assertAlmostEqual(prm.get("salt", 2029)["threshold"], 520302.005)
        self.assertFalse(prm.get("salt", 2030)["phasedown"])


class Depletion(unittest.TestCase):
    def test_unfunded(self):
        raw = single_household(1950, [{"id": "cash", "owner": "p", "type": "cash", "balance": 1000}],
                               spending=5000, last=2026)
        r = row(E.run(raw), 2026)
        self.assertEqual(r["balances"]["cash"], 0)
        self.assertEqual(r["unfunded_spending"], 4000)


class InputChecks(unittest.TestCase):
    def test_inherited_conversion_rejected(self):
        raw = single_household(1960, [
            {"id": "inh", "owner": "p", "type": "inherited_ira", "balance": 1000,
             "inherited": {"from_born": 1940, "died": 2024, "beneficiary_class": "designated"}}],
            actions=[{"type": "roth_conversion", "from": "inh", "amount": 100, "years": [2026]}])
        with self.assertRaises(E.InputError):
            E.run(raw)


class Projection(unittest.TestCase):
    """14.1: unrounded chain from the last published value, then round."""

    def test_standard_deduction_chain(self):
        prm = Params(inflation=0.03)
        self.assertEqual(prm.get("standard_deduction", 2027)["mfj"], 33150)   # 33,166 -> down to $50
        self.assertEqual(prm.get("standard_deduction", 2028)["mfj"], 34150)   # 34,160.98 (not 33,150 x 1.03)
        self.assertEqual(prm.projected_years, {2027, 2028})

    def test_published_years_not_projected(self):
        prm = Params()
        prm.get("ordinary_brackets", 2026)
        prm.get("ss_cola", 2027)
        prm.get("salt", 2028)
        self.assertEqual(prm.projected_years, set())


# ---------------------------------------------------------------------------------------------------------
# v1.3 / v1.4 changes (CHANGES-v1.2-to-v1.4.diff): survivor claim age (5.5), a spouse who died before the
# plan (5.7), the earnings test (5.8), and pre-SECURE inherited IRAs (6A.9)
# ---------------------------------------------------------------------------------------------------------
def no_cola(raw):
    return E.run(raw, Params(inflation=0.0, cola=0.0, overrides={"ss_cola": 0.0}))


class SurvivorClaimAgeAndLateSpouse(unittest.TestCase):
    """5.5 (v1.3) survivor_claim_age and claim_survivor_benefit; 5.7 a spouse who died before the plan."""

    def widow(self, survivor_claim_age=None, actions=None):
        raw = Example8Survivor.scenario(self, 1960, 70, 1964, 500, 67, 2025, 2026, 2031)
        if survivor_claim_age is not None:
            raw["household"]["people"][1]["social_security"]["survivor_claim_age"] = survivor_claim_age
        raw["plans"][0]["actions"] = actions or []
        return no_cola(raw)

    def test_default_survivor_claim_at_60(self):
        # d (PIA 2,000) dies in 2025 before he claims at 70, so his base is 2,000 with no delayed credits (5.5).
        # s starts at 60 (Jan 2026), 60 months early on a 67 FRA: reduction 28.5% x 60/84 = 20.357%;
        # 2,000 x (1 - 0.20357) = 1,592.86 -> 1,592 a month. 2026: 12 x 1,592 = 19,104.
        out = self.widow()
        self.assertEqual(row(out, 2026, "A")["social_security"]["s"], 1592 * 12)

    def test_survivor_claim_age_67_has_no_reduction(self):
        # survivor_claim_age 67 (804 months): s was born 1964, so age 67 is Jan 2031. Nothing before that; from
        # Jan 2031 the full 2,000 with no reduction (larger than s's own 500): 2,000 x 12 = 24,000.
        out = self.widow(survivor_claim_age=67)
        self.assertEqual(row(out, 2030, "A")["social_security"]["s"], 0)
        self.assertEqual(row(out, 2031, "A")["social_security"]["s"], 2000 * 12)

    def test_claim_survivor_benefit_action_matches_the_input(self):
        out = self.widow(actions=[{"type": "claim_survivor_benefit", "person": "s", "age": 67}])
        self.assertEqual(row(out, 2031, "A")["social_security"]["s"], 2000 * 12)
        self.assertEqual(row(out, 2030, "A")["social_security"]["s"], 0)

    def late_raw(self, died=2020, survivor_claim_age=66.6667):
        """Single worker born Jan 1960 (FRA 67; PIA 2,000, claims at 67). Late spouse born Jan 1950, died 2020,
        PIA 1,000 at FRA, never claimed."""
        person = {"id": "p", "born": 1960, "born_month": 1, "medicare": False,
                  "social_security": {"monthly_at_fra": 2000, "claim_age": 67,
                                      "survivor_claim_age": survivor_claim_age},
                  "late_spouse": {"born": 1950, "born_month": 1, "died": died, "monthly_at_fra": 1000}}
        return {
            "household": {"filing": "single", "state": "none", "people": [person],
                          "accounts": [{"id": "cash", "owner": "p", "type": "cash", "balance": 0}],
                          "income": [], "spending_need": 0,
                          "itemized": {"salt_other": 0, "mortgage_interest": 0, "medical": 0, "charity_cash": 0}},
            "plans": [{"name": "A", "actions": []}], "events": [],
            "assumptions": {"return": 0.0, "inflation": 0.0, "first_year": 2026, "last_year": 2027,
                            "heirs_tax_rate": 0.0, "switches": {}},
        }

    def test_late_spouse_survivor_benefit(self):
        # Late spouse died Jan 2020 at 70 (Nov 2020 = 850 months from birth on Jan 1950, 840 cap, FRA 66 = 792):
        # 48 delayed months x 2/3% = 32%; PIA 1,000 x 1.32 = 1,320 (never claimed, so no widow's limit).
        # Survivor claims at 66.6667 = 800 months = survivor FRA, so no reduction; from Sep 2026 (month 800 after
        # Jan 1960) the 1,320 is paid, which beats nothing: 4 months = 5,280 in 2026. In 2027 her own 2,000 is
        # bigger, so 2,000 x 12 = 24,000.
        out = no_cola(self.late_raw())
        self.assertEqual(row(out, 2026, "A")["social_security"]["p"], 4 * 1320)
        self.assertEqual(row(out, 2027, "A")["social_security"]["p"], 2000 * 12)
        self.assertEqual(out["plans"]["A"]["years"][0]["alive"], {"p": True})   # the late spouse is not a person

    def test_late_spouse_claim_action_form(self):
        raw = self.late_raw(survivor_claim_age=None)
        raw["plans"][0]["actions"] = [{"type": "claim_survivor_benefit", "person": "p", "age": 66.6667}]
        self.assertEqual(row(no_cola(raw), 2026, "A")["social_security"]["p"], 4 * 1320)

    def test_late_spouse_input_checks(self):
        with self.assertRaises(E.InputError):
            E.run(self.late_raw(died=2026))                  # died in the plan, not before it
        raw = self.late_raw()
        raw["household"]["filing"] = "mfj"
        raw["household"]["people"].append({"id": "q", "born": 1961, "medicare": False})
        with self.assertRaises(E.InputError):
            E.run(raw)                                       # a late spouse only in a single household


class EarningsTest(unittest.TestCase):
    """5.8 (v1.4). Born June 1960: FRA 67 is June 2027 (the year FRA is reached: k = 5 months before it).
    Claims at 62: PIA 1,000 x 0.70 = 700 a month. Wages are the only income."""

    def raw(self, wages, first=2026, last=2028, switches=None):
        person = {"id": "p", "born": 1960, "born_month": 6, "medicare": False,
                  "social_security": {"monthly_at_fra": 1000, "claim_age": 62}}
        income = [{"type": "wages", "owner": "p", "annual": amt, "start_year": y, "end_year": y}
                  for y, amt in wages.items()]
        return {
            "household": {"filing": "single", "state": "none", "people": [person],
                          "accounts": [{"id": "cash", "owner": "p", "type": "cash", "balance": 0}],
                          "income": income, "spending_need": 0,
                          "itemized": {"salt_other": 0, "mortgage_interest": 0, "medical": 0, "charity_cash": 0}},
            "plans": [{"name": "A", "actions": []}], "events": [],
            "assumptions": {"return": 0.0, "inflation": 0.0, "first_year": first, "last_year": last,
                            "heirs_tax_rate": 0.0, "switches": dict(switches or {})},
        }

    def ss(self, out, year):
        return row(out, year, "A")["social_security"]["p"]

    def test_before_fra_limit_24480(self):
        # 2026 wages 31,480: excess = (31,480 - 24,480) / 2 = 3,500. Withhold whole payments from January:
        # 5 x 700 = 3,500 (stop, since it is at least the excess). 2026 paid: 7 x 700 = 4,900.
        # Credit back: 5 withheld months -> claim age 62 + 5 months: early 55 months, reduction 20% + 19 x 5/12%
        # = 27.9167%, factor 0.720833; from June 2027 the own benefit is 720.80, paid as 720 (whole dollars).
        # 2027: Jan-May 5 x 700 = 3,500 and Jun-Dec 7 x 720 = 5,040, total 8,540. 2028: 12 x 720 = 8,640.
        out = no_cola(self.raw({2026: 31480}))
        self.assertEqual(self.ss(out, 2026), 4900)
        self.assertEqual(self.ss(out, 2027), 8540)
        self.assertEqual(self.ss(out, 2028), 8640)

    def test_fra_year_limit_65160(self):
        # 2027 (the year FRA is reached) wages 160,704: k = 5 months before June. Excess =
        # (160,704 x 5/12 - 65,160) / 3 = (66,960 - 65,160) / 3 = 600. Jan's 700 covers it: 1 month withheld.
        # Feb-May paid 4 x 700 = 2,800; from June the own benefit has one credited month: claim age 745 months,
        # early 59 months, reduction 20% + 23 x 5/12% = 29.5833%, factor 0.704167 -> 704 a month.
        # 2027 = 2,800 + 7 x 704 = 7,728. 2028 = 12 x 704 = 8,448.
        out = no_cola(self.raw({2027: 160704}))
        self.assertEqual(self.ss(out, 2026), 8400)
        self.assertEqual(self.ss(out, 2027), 7728)
        self.assertEqual(self.ss(out, 2028), 8448)

    def test_switch_false_is_v13(self):
        # ss_earnings_test false: nothing is withheld and nothing is credited (v1.3 behaviour)
        out = no_cola(self.raw({2026: 31480}, switches={"ss_earnings_test": False}))
        self.assertEqual([self.ss(out, y) for y in (2026, 2027, 2028)], [8400, 8400, 8400])

    def test_2025_limit_published(self):
        # v1.4.1: 2025 under FRA is $23,400. Wages 33,000: excess = (33,000 - 23,400) / 2 = 4,800. Withhold
        # Jan-Jul (7 x 700 = 4,900 covers it; 6 x 700 = 4,200 does not). 2025 paid: 5 x 700 = 3,500.
        out = no_cola(self.raw({2025: 33000}, first=2025, last=2025))
        self.assertEqual(self.ss(out, 2025), 3500)

    def test_fra_year_credit_counts_earlier_withheld_months(self):
        # v1.4.1: months withheld in the FRA year before the FRA month count for the credit from the FRA month on.
        # 2027 wages 163,584: k = 5, excess = (163,584 x 5/12 - 65,160) / 3 = (68,160 - 65,160) / 3 = 1,000.
        # Jan 700 is not enough; Jan + Feb 1,400 is. So 2 months withheld: Jan and Feb. Mar-May paid 3 x 700 = 2,100.
        # Credit count is 2 from June on: claim age 746 months, early 58, reduction 20% + 22 x 5/12% = 29.1667%,
        # factor 0.708333 -> 708.30 -> 708. 2027 = 2,100 + 7 x 708 = 7,056. 2028 = 12 x 708 = 8,496.
        out = no_cola(self.raw({2027: 163584}))
        self.assertEqual(self.ss(out, 2027), 7056)
        self.assertEqual(self.ss(out, 2028), 8496)

    def test_limits_after_2026_grow_with_inflation(self):
        # 14.1 chain from the published 2026 values, rounded to $120:
        # under FRA 2027: 24,480 x 1.03 = 25,214.40 -> nearest $120 = 25,200 (210 x 120)
        # FRA year 2027: 65,160 x 1.03 = 67,114.80 -> nearest $120 = 67,080 (559 x 120)
        prm = Params(inflation=0.03)
        self.assertEqual(prm.get("ss_earnings_under", 2026), 24480)
        self.assertEqual(prm.get("ss_earnings_under", 2027), 25200)
        self.assertEqual(prm.get("ss_earnings_fra_year", 2027), 67080)
        self.assertEqual(prm.projected_years, {2027})

    def test_2025_values_are_published(self):
        prm = Params(inflation=0.03)
        self.assertEqual(prm.get("ss_earnings_under", 2025), 23400)
        self.assertEqual(prm.get("ss_earnings_fra_year", 2025), 62160)
        self.assertEqual(prm.projected_years, set())
        with self.assertRaises(E.InputError):
            E.limit(prm, "ss_earnings_under", 2024)


class PreSecureInheritedIra(unittest.TestCase):
    """6A.9 (v1.3): an owner who died before 2020 keeps the pre-SECURE stretch. Owner born 1945, died 2018 (after
    the RBD, which was 2016), so the RBD test passes. Designated beneficiary born 1975."""

    def sched(self, cls, born, died=2018):
        acc = {"type": "inherited_ira", "inherited": {"from_born": 1945, "died": died, "beneficiary_class": cls}}
        return E.inherited_setup(acc, {"born": born}, E.default_switches("single", "none"))

    def test_designated_annual_no_deadline(self):
        s = self.sched("designated", 1975)
        self.assertTrue(s["rbd"])
        self.assertIsNone(s["deadline"])                     # not D + 10 = 2028
        self.assertEqual(s["start"], 2019)
        # 2030 divisor: beneficiary (born 1975, age 44 in 2019) minus one for each year after 2019 = S(44) - 11;
        # owner's remaining life expectancy at death (age 73) less 12 years = S(73) - 12; the longer one counts.
        le_b = P.single_life(44) - (2030 - 2019)
        le_o = P.single_life(73) - (2030 - 2018)
        self.assertAlmostEqual(E.inherited_rmd(s, 2030, 100000, 100000, Params()), 100000 / max(le_b, le_o))
        self.assertGreater(E.inherited_rmd(s, 2040, 100000, 100000, Params()), 0)   # still distributing in 2040

    def test_minor_child_has_no_age_21_deadline(self):
        # post-2019 rules would end this child's account 10 years after age 21 (2005 + 21 + 10 = 2036)
        s = self.sched("minor_child", 2005)
        self.assertIsNone(s["deadline"])
        self.assertTrue(s["annual"])

    def test_successor_after_2019_gets_ten_years(self):
        # The designated beneficiary dies in 2025 (after 2019): SECURE Act 401(b)(5) gives 2025 + 10 = 2035.
        s = self.sched("designated", 1975)
        st = {"acc": {"ia": {"id": "ia", "owner": "d", "type": "inherited_ira", "bal": 1000.0, "basis": 0.0,
                             "sched": s}},
              "order": ["ia"], "basis8606": {"d": 0.0, "s": 0.0}, "deferred": {},
              "roth": {"d": {"first": None, "contrib": 0.0, "layers": []},
                       "s": {"first": None, "contrib": 0.0, "layers": []}}}
        sc = {"switches": E.default_switches("mfj", "none"), "deaths": {"d": 2025}}
        E.apply_death(st, sc, "d", "s")
        self.assertEqual(st["acc"]["ia"]["sched"]["deadline"], 2035)


if __name__ == "__main__":
    unittest.main()
