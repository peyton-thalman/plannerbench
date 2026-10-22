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


if __name__ == "__main__":
    unittest.main()
