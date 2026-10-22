#!/usr/bin/env python3
"""Clean-room retirement tax engine implementing spec/RULES.md (input/output per CONTRACT.md).

Usage:  python3 -I checks/cleanroom/engine.py scenario.json  > result.json

Standard library only. Written from RULES.md, the law tables in spec/law/, and primary sources cited in
params.py; never from the other engine. Section numbers in comments and docstrings refer to RULES.md.
"""

import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir from sys.path

import params as P  # noqa: E402
from params import Params, floor_to  # noqa: E402

PRETAX_TYPES = ("traditional_ira", "401k", "inherited_ira")
ROTH_TYPES = ("roth_ira", "inherited_roth_ira")
EDB_CLASSES = ("spouse", "minor_child", "disabled", "chronically_ill", "not_more_than_10_years_younger")
ALL_CLASSES = EDB_CLASSES + ("designated", "non_designated")
INCOME_TYPES = ("wages", "pension", "annuity_taxable", "interest_taxable", "interest_tax_exempt", "rental")
SURVIVING_INCOME = ("rental", "interest_taxable", "interest_tax_exempt")  # 1.3: continue after owner's death


class InputError(ValueError):
    pass


def max0(x):
    return x if x > 0 else 0.0


# =========================================================================================================
# Section 1 — inputs
# =========================================================================================================
def default_switches(filing, state):
    """Appendix B defaults."""
    return {
        "use_tax_table": False,
        "defer_first_rmd": False,
        "spouse_is_sole_beneficiary": filing == "mfj",
        "edb_elects_10_year": False,
        "spouse_401k_to_ira": True,
        "community_property": False,                # v1.2 (3.3 step 5)
        "ss_dollar_rounding": True,
        "round_8606_ratio_3dp": False,
        "annuity_is_nii": True,
        "az_senior_subtraction": True,
        "az_ltcg_acquired_after_2011": True,
        "az_pension_is_government": False,
        "az_assume_future_conformity": True,
        "heirs_credit_8606_basis": False,
    }


def normalize(raw):
    """Read the Section 1 input into one dict, applying the defaults for the added fields."""
    hh = raw["household"]
    asm = raw.get("assumptions", {})
    filing = hh["filing"]
    if filing not in ("mfj", "single"):
        raise InputError("household.filing must be mfj or single")
    state = hh.get("state", "none")
    if state not in ("AZ", "none"):
        raise InputError("household.state must be AZ or none")
    people = {}
    for p in hh["people"]:
        people[p["id"]] = {"id": p["id"], "born": int(p["born"]), "born_month": int(p.get("born_month", 1)),
                           "medicare": bool(p.get("medicare", False)), "ss": p.get("social_security")}
    if len(people) != (2 if filing == "mfj" else 1):
        raise InputError("mfj needs exactly two people, single exactly one")
    pids = list(people)
    accounts = []
    for a in hh.get("accounts", []):
        t = a["type"]
        if t not in PRETAX_TYPES + ROTH_TYPES + ("taxable", "cash"):
            raise InputError("unknown account type %s" % t)
        owner = a["owner"]
        if owner == "joint":
            if t not in ("taxable", "cash"):
                raise InputError("only taxable and cash accounts may be joint (1.2)")
            if filing == "single":
                owner = pids[0]  # 1.2: a joint account in a single household is the one person's
        elif owner not in people:
            raise InputError("account %s owner %s unknown" % (a["id"], owner))
        bal = float(a.get("balance", 0.0))
        acc = {"id": a["id"], "owner": owner, "type": t, "bal": bal,
               "basis": float(a["cost_basis"]) if a.get("cost_basis") is not None else bal,
               "dy": float(a.get("dividend_yield", 0.0)), "qs": float(a.get("qualified_share", 1.0)),
               "after_tax_basis": float(a.get("after_tax_basis", 0.0)),
               "first_roth_year": a.get("first_roth_year"),
               "contribution_basis": float(a.get("contribution_basis", 0.0)),
               "conversion_layers": a.get("conversion_layers", []),
               "inherited": a.get("inherited"), "titling": a.get("titling")}
        if acc["titling"] not in (None, "community", "community_with_survivorship", "jtwros"):
            raise InputError("account %s: unknown titling" % a["id"])
        if t in ("inherited_ira", "inherited_roth_ira"):
            inh = acc["inherited"] or {}
            if inh.get("beneficiary_class") not in ALL_CLASSES:
                raise InputError("account %s: unknown beneficiary_class" % a["id"])
        accounts.append(acc)
    if len({a["id"] for a in accounts}) != len(accounts):
        raise InputError("duplicate account ids")
    income = []
    for it in hh.get("income", []):
        t = it.get("type", it.get("kind"))
        if t not in INCOME_TYPES:
            raise InputError("unknown income type %s" % t)
        if t == "rental" and float(it["annual"]) < 0:
            raise InputError("rental must be >= 0 (1.3)")
        income.append({"type": t, "owner": it.get("owner"), "annual": float(it["annual"]),
                       "start_year": it.get("start_year"), "end_year": it.get("end_year"),
                       "cola": float(it.get("cola", 0.0))})
    deaths = {}
    for e in raw.get("events", []):
        if e["type"] == "death":
            if e["person"] not in people:
                raise InputError("death of unknown person")
            deaths[e["person"]] = int(e["year"])
    switches = default_switches(filing, state)
    switches.update(asm.get("switches", {}) or {})
    first_year, last_year = int(asm["first_year"]), int(asm["last_year"])
    inflation = float(asm.get("inflation", 0.0))
    sc = {
        "filing": filing, "state": state, "people": people, "pids": pids, "accounts": accounts,
        "income": income, "deaths": deaths, "switches": switches,
        "spending_need": float(hh.get("spending_need", 0.0)),
        "itemized": {k: float((hh.get("itemized") or {}).get(k, 0.0))
                     for k in ("salt_other", "mortgage_interest", "medical", "charity_cash")},
        "prior_magi": {int(k): v for k, v in (hh.get("prior_magi") or {}).items()},
        "prior_cap_loss": float(hh.get("prior_capital_loss_carryover", 0.0)),
        "return": float(asm.get("return", 0.0)), "inflation": inflation,
        "first_year": first_year, "last_year": last_year,
        "heirs_tax_rate": float(asm.get("heirs_tax_rate", 0.0)),
        "chained_cpi_gap": float(asm.get("chained_cpi_gap", 0.0)),
        "medicare_growth": asm.get("medicare_growth"), "cola": asm.get("cola"),
        "survivor_spending_ratio": float(asm.get("survivor_spending_ratio", 1.0)),
        "part_d_base_monthly": float(asm.get("part_d_base_monthly", 0.0)),
        "az_muni_in_state_share": float(asm.get("az_muni_in_state_share", 0.0)),
    }
    return sc


def validate_plan(sc, plan):
    """1.5: a conversion must come from a traditional_ira or 401k; from an inherited IRA it is an input error."""
    types = {a["id"]: a["type"] for a in sc["accounts"]}
    for act in plan.get("actions", []):
        if act["type"] == "roth_conversion":
            t = types.get(act["from"])
            if t in ("inherited_ira", "inherited_roth_ira"):
                raise InputError("Roth conversion from an inherited IRA is not permitted (IRC §408(d)(3)(C))")
            if t not in ("traditional_ira", "401k"):
                raise InputError("roth_conversion from must be traditional_ira or 401k")
        elif act["type"] not in ("qcd", "withdrawal", "harvest_gains", "claim_social_security"):
            raise InputError("unknown action type %s" % act["type"])


# =========================================================================================================
# Section 3.1 — status
# =========================================================================================================
def age(person, Y):
    return Y - person["born"]


def half_year(person, whole):
    """Calendar year in which the person reaches `whole` and a half (3.1 construction)."""
    return person["born"] + whole if person["born_month"] <= 6 else person["born"] + whole + 1


def over_59h(person, Y):
    return half_year(person, 59) <= Y


def over_70h(person, Y):
    return half_year(person, 70) <= Y


def is65(person, Y):
    return age(person, Y) >= 65


def medicare_months(person, Y):
    if not person["medicare"]:
        return 0
    a = age(person, Y)
    if a > 65:
        return 12
    if a == 65:
        return 13 - person["born_month"]
    return 0


def alive_in(sc, pid, Y):
    d = sc["deaths"].get(pid)
    return d is None or d >= Y


def spouse_of(sc, pid):
    others = [q for q in sc["pids"] if q != pid]
    return others[0] if sc["filing"] == "mfj" and others else None


# =========================================================================================================
# Section 5 — Social Security
# =========================================================================================================
def own_factor(claim_months, fra_months, prm):
    """5.3: early reduction or delayed retirement credits."""
    early = max0(fra_months - claim_months)
    if early > 0:
        return 1 - (prm.const("ss_early_rate_1") * min(early, 36) + prm.const("ss_early_rate_2") * max0(early - 36))
    late = max0(min(claim_months, prm.const("ss_max_drc_months")) - fra_months)
    return 1 + prm.const("ss_drc_monthly_rate") * late


def ss_schedule(sc, plan, prm, years):
    """Sections 5.2-5.6: annual benefits {pid: {Y: amount}} for this plan."""
    first = sc["first_year"]
    sw = sc["switches"]
    claims = {a["person"]: float(a["age"]) for a in plan.get("actions", [])
              if a["type"] == "claim_social_security"}
    info = {}
    for pid, p in sc["people"].items():
        ss = p["ss"]
        if not ss:
            continue
        base_abs = p["born"] * 12 + p["born_month"] - 1        # absolute month index at age 0 months
        fra = P.ss_fra_months(p["born"])
        pia, v = {}, float(ss["monthly_at_fra"])
        for Y in years:                                         # 5.2
            if Y > first:
                v = floor_to(v * (1 + prm.get("ss_cola", Y)), 0.10)
            pia[Y] = v
        already = ss.get("already_claimed_monthly")
        own = {}
        if already is not None:                                 # 5.3 last bullet; 1.1 claimed_at_months
            cam = ss.get("claimed_at_months")
            if cam is not None:
                factor = own_factor(int(cam), fra, prm)
                start_abs = base_abs + int(cam)
            else:
                # v1.2: the ratio itself, so delayed credits above 1 are kept (20 CFR 404.313(e)(1))
                factor = float(already) / float(ss["monthly_at_fra"]) if ss["monthly_at_fra"] else 1.0
                start_abs = -10 ** 9
            v = float(already)
            for Y in years:
                if Y > first:
                    v = floor_to(v * (1 + prm.get("ss_cola", Y)), 0.10)
                own[Y] = v
            own_start = -10 ** 9                                 # entitled for all of first_year
        else:
            ca = claims.get(pid, ss.get("claim_age", fra / 12.0))
            cm = int(math.floor(12 * float(ca) + 0.5))
            cm = min(max(cm, prm.const("ss_min_claim_months")), prm.const("ss_max_drc_months"))
            factor = own_factor(cm, fra, prm)
            start_abs = base_abs + cm
            own_start = start_abs
            for Y in years:
                own[Y] = floor_to(pia[Y] * factor, 0.10)
        info[pid] = {"base_abs": base_abs, "fra": fra, "sfra": P.ss_survivor_fra_months(p["born"]),
                     "pia": pia, "own": own, "factor": factor, "start": start_abs, "own_start": own_start,
                     "already": already is not None}

    out = {pid: {Y: 0.0 for Y in years} for pid in sc["people"]}
    for pid, me in info.items():
        q = spouse_of(sc, pid)
        qi = info.get(q) if q else None
        # 5.4 spousal set-up
        sp_start, sp_red = None, 0.0
        if qi is not None and not me["already"]:
            sp_start = max(me["own_start"], qi["start"])
            early_sp = max0(me["fra"] - (sp_start - me["base_abs"]))
            sp_red = (prm.const("ss_spousal_rate_1") * min(early_sp, 36)
                      + prm.const("ss_early_rate_2") * max0(early_sp - 36))
        # 5.5 survivor set-up
        D = sc["deaths"].get(q) if q else None
        sv = None
        if qi is not None and D is not None and alive_in(sc, pid, D + 1):
            s_start = max((D + 1) * 12, me["base_abs"] + prm.const("ss_survivor_min_months"))
            early_s = max0(me["sfra"] - (s_start - me["base_abs"]))
            red_s = (prm.const("ss_survivor_max_reduction") * early_s
                     / (me["sfra"] - prm.const("ss_survivor_min_months")))
            claimed = qi["start"] <= D * 12 + 11
            if claimed:
                drc_mult = max(1.0, qi["factor"])
            else:
                am = D * 12 + 10 - qi["base_abs"]   # v1.2: age in months in November of D
                drc_mult = 1 + prm.const("ss_drc_monthly_rate") * max0(
                    min(am, prm.const("ss_max_drc_months")) - qi["fra"])
            sv = {"start": s_start, "red": red_s, "claimed": claimed, "mult": drc_mult}
        for Y in years:
            if not alive_in(sc, pid, Y):
                continue
            both = qi is not None and alive_in(sc, q, Y)
            spousal = 0.0
            if both and sp_start is not None:
                excess = max0(prm.const("ss_spousal_rate") * qi["pia"][Y] - me["pia"][Y])
                spousal = floor_to(excess * (1 - sp_red), 0.10)
            surv = 0.0
            if sv is not None and Y > D:
                widow = qi["pia"][Y] * sv["mult"] * (1 - sv["red"])
                if sv["claimed"] and qi["factor"] < 1:          # widow's limit (RIB-LIM)
                    widow = min(widow, max(qi["own"][Y], prm.const("ss_rib_lim_rate") * qi["pia"][Y]))
                surv = floor_to(widow, 0.10)
            total = 0.0
            for m in range(12):
                a = Y * 12 + m
                entitled = a >= me["own_start"]
                own_m = me["own"][Y] if entitled else 0.0
                if both:
                    pay = own_m + (spousal if (entitled and sp_start is not None and a >= sp_start) else 0.0)
                elif sv is not None and Y > D:
                    pay = max(own_m, surv if a >= sv["start"] else 0.0)
                else:
                    pay = own_m
                if sw["ss_dollar_rounding"]:
                    pay = floor_to(pay, 1.0)
                total += pay
            out[pid][Y] = total
    return out


# =========================================================================================================
# Section 6 — RMDs from the owner's own accounts
# =========================================================================================================
def first_rmd_year(born, born_month):
    """6.1: the year the applicable age is reached."""
    aa = P.rmd_applicable_age(born, born_month)
    if aa == 70.5:
        return born + 70 if born_month <= 6 else born + 71
    return born + aa


def owner_rmd(sc, acc, Y, B0, grown):
    """6.2: B0 / divisor (Uniform Lifetime, or Joint and Last Survivor when the spouse is the sole beneficiary
    and more than 10 years younger), capped at the grown balance."""
    owner = sc["people"][acc["owner"]]
    if Y < first_rmd_year(owner["born"], owner["born_month"]):
        return 0.0
    a = age(owner, Y)
    div = P.uniform_divisor(a)
    q = spouse_of(sc, acc["owner"])
    if (q and sc["switches"]["spouse_is_sole_beneficiary"] and alive_in(sc, q, Y)   # married on Jan 1 of Y
            and a - age(sc["people"][q], Y) > 10):
        div = P.joint_divisor(a, age(sc["people"][q], Y))
    return min(B0 / div, grown)


# =========================================================================================================
# Section 6A — inherited IRAs and inherited Roth IRAs
# =========================================================================================================
def inherited_setup(acc, holder, sw):
    """6A.1-6A.4: fix the distribution schedule when the account enters the model."""
    inh = acc["inherited"]
    D, fb, cls = int(inh["died"]), int(inh["from_born"]), inh["beneficiary_class"]
    owner_fry = first_rmd_year(fb, 1)                     # 6A.1: born_month = 1 for the original owner
    if acc["type"] == "inherited_roth_ira":
        rbd = False                                       # 6A.1 / 6A.8
    elif inh.get("owner_had_reached_rbd") is not None:
        rbd = bool(inh["owner_had_reached_rbd"])
    else:
        rbd = D >= owner_fry + 1                          # reading: death in the RBD year is after April 1
    s = {"D": D, "fb": fb, "cls": cls, "rbd": rbd, "ben_born": holder["born"], "deadline": None,
         "annual": False, "start": D + 1, "div": None, "frozen": None}
    ten = sw["edb_elects_10_year"] and cls in EDB_CLASSES and not rbd
    s["edb_life_expectancy"] = cls in EDB_CLASSES and not ten          # 6A.6 v1.2
    if cls == "designated" or ten:
        s["deadline"] = D + 10
        s["annual"] = rbd
        s["div"] = "max_b_o"
    elif cls == "non_designated":
        if rbd:
            s["annual"], s["div"] = True, "o"
        else:
            s["deadline"] = D + 5
    elif cls == "spouse":
        s["annual"] = True
        if rbd:
            s["div"] = "max_s_o"
        else:
            s["div"] = "s"
            s["start"] = max(D + 1, owner_fry)
    else:  # minor_child, disabled, chronically_ill, not_more_than_10_years_younger
        s["annual"] = True
        s["div"] = "max_b_o" if rbd else "b"
        if cls == "minor_child":
            s["deadline"] = holder["born"] + 21 + 10      # 10th year after the year the child reaches 21
    return s


def inherited_rmd(s, Y, B0, grown, prm):
    """6A.3-6A.5: this year's required distribution from one inherited account."""
    D = s["D"]
    if Y <= D:
        return 0.0
    if s["deadline"] is not None and Y >= s["deadline"]:
        return grown                                      # 6A.7: the deadline year takes everything
    if not s["annual"] or Y < s["start"]:
        return 0.0
    if (s["cls"] == "designated" and s["rbd"] and 2020 <= D <= 2023
            and Y in prm.const("inherited_rmd_waiver_years")):
        return 0.0                                        # 6A.5
    le_b = P.single_life(D + 1 - s["ben_born"]) - (Y - (D + 1))
    le_o = P.single_life(D - s["fb"]) - (Y - D)
    if s["frozen"] is None:
        le_s = P.single_life(Y - s["ben_born"])
    else:                                                 # 6A.6 reading: recalculation stops at death
        le_s = P.single_life(s["frozen"] - s["ben_born"]) - (Y - s["frozen"])
    div = {"b": le_b, "o": le_o, "s": le_s, "max_b_o": max(le_b, le_o), "max_s_o": max(le_s, le_o)}[s["div"]]
    if div <= 1:
        return grown
    return min(B0 / div, grown)


# =========================================================================================================
# Section 7 helpers
# =========================================================================================================
def sell_taxable(acc, w):
    """7.7: average-cost sale of w; returns the (possibly negative) gain."""
    V, C = acc["bal"], acc["basis"]
    if w <= 0 or V <= 0:
        return 0.0
    w = min(w, V)
    gain = w * (1 - C / V)
    acc["basis"] = C * (1 - w / V)
    acc["bal"] = V - w
    return gain


def roth_take(ledger, amount, Y, qualified, under_59h, beneficiary):
    """7.5 ordering: contributions, conversion layers (oldest first, taxable part first), then earnings.
    Returns (taxable_earnings, amount_subject_to_10pct). The ledger is consumed even for qualified
    distributions (Section 11)."""
    rem = amount
    taxable = penalty = 0.0
    t = min(rem, ledger["contrib"])
    ledger["contrib"] -= t
    rem -= t
    for layer in sorted(ledger.get("layers", []), key=lambda L: L[0]):
        if rem <= 0:
            break
        t = min(rem, layer[1])
        layer[1] -= t
        rem -= t
        if not qualified and under_59h and Y < layer[0] + 5:
            penalty += t
        t = min(rem, layer[2])
        layer[2] -= t
        rem -= t
    if rem > 0 and not qualified:
        taxable += rem
        if under_59h and not beneficiary:
            penalty += rem
    return taxable, penalty


# =========================================================================================================
# Section 9 — federal income tax
# =========================================================================================================
def ordinary_tax(x, brackets):
    """Tax Computation Worksheet over ordinary_brackets."""
    if x <= 0:
        return 0.0
    tax, lo = 0.0, 0.0
    for up, rate in brackets:
        if up is None or x <= up:
            return tax + (x - lo) * rate
        tax += (up - lo) * rate
        lo = up
    return tax


def taxable_social_security(ss_total, agi_ex_ss, tax_exempt, filing, prm):
    """9.3 Pub 915 Worksheet 1 / IRC §86."""
    if ss_total <= 0:
        return 0.0
    st = prm.const("ss_tax")
    r1, r2 = st["first_rate"], st["second_rate"]
    provisional = agi_ex_ss + tax_exempt + r1 * ss_total
    base, adj = st["base_amount"][filing], st["adjusted_base_amount"][filing]
    if provisional <= base:
        return 0.0
    if provisional <= adj:
        return min(r1 * ss_total, r1 * (provisional - base))
    return min(r2 * ss_total, r2 * (provisional - adj) + min(r1 * ss_total, r1 * (adj - base)))


def form8606(basis, line6, line7, line8, round3=False):
    """9.5 Form 8606 Part I/II for one person. Returns dict of lines 9-18."""
    line3 = basis
    line9 = line6 + line7 + line8
    if line9 <= 0:
        return {"line9": 0.0, "line10": 0.0, "line11": 0.0, "line12": 0.0, "line14": line3,
                "line15c": line7, "line18": line8}
    ratio = min(1.0, line3 / line9)
    if round3:
        ratio = math.floor(ratio * 1000 + 0.5) / 1000.0
    line11, line12 = line8 * ratio, line7 * ratio
    return {"line9": line9, "line10": ratio, "line11": line11, "line12": line12,
            "line14": line3 - (line11 + line12), "line15c": line7 - line12, "line18": line8 - line11}


def senior_deduction(Y, magi, n65, filing, prm):
    """9.10 Schedule 1-A Part V: the reduction comes off each qualifying person's amount separately."""
    sd = prm.const("senior_deduction")
    if not (sd["first_year"] <= Y <= sd["last_year"]):
        return 0.0
    reduction = sd["phaseout_rate"] * max0(magi - sd["threshold"][filing])
    return n65 * max0(sd["amount"] - reduction)


def salt_cap_amount(Y, magi, prm):
    """9.8 SALT limitation incl. the phase-down (IRC §164(b)(7))."""
    s = prm.get("salt", Y)
    cap = s["cap"]
    if s["phasedown"]:
        cap = max(prm.const("salt_floor"), cap - prm.const("salt_phasedown_rate") * max0(magi - s["threshold"]))
    return cap


def itemized_limit_reduction(itemized_pre, agi_less_senior, b37_start, rate):
    """9.8 §68 (OBBBA): rate x min(itemized, TI_pre + itemized - start of the 37% bracket)."""
    return rate * min(itemized_pre, max0(agi_less_senior - b37_start))


def qdcg_tax(TI, QD, CG, brackets, zero_max, fifteen_max, r15, r20):
    """9.11 Qualified Dividends and Capital Gain Tax Worksheet. Returns (tax, lines)."""
    L1, L2, L3 = TI, QD, CG
    L4 = L2 + L3
    L5 = max0(L1 - L4)
    L6 = zero_max
    L7 = min(L1, L6)
    L8 = min(L5, L7)
    L9 = L7 - L8
    L10 = min(L1, L4)
    L11 = L9
    L12 = L10 - L11
    L13 = fifteen_max
    L14 = min(L1, L13)
    L15 = L5 + L9
    L16 = max0(L14 - L15)
    L17 = min(L12, L16)
    L18 = L17 * r15
    L19 = L9 + L17
    L20 = L10 - L19
    L21 = L20 * r20
    L22 = ordinary_tax(L5, brackets)
    L23 = L18 + L21 + L22
    L24 = ordinary_tax(L1, brackets)
    return min(L23, L24), {"L5": L5, "L9": L9, "L17": L17, "L20": L20}


def regular_tax(Y, filing, TI, QD, CG, prm):
    brackets = prm.get("ordinary_brackets", Y)[filing]
    if QD + CG <= 0:
        return ordinary_tax(TI, brackets)
    cg = prm.get("cg_thresholds", Y)[filing]
    tax, _ = qdcg_tax(TI, QD, CG, brackets, cg["zero_max"], cg["fifteen_max"],
                      prm.const("cg_rate_15"), prm.const("cg_rate_20"))
    return tax


def irmaa_tier(magi, bounds):
    """12.3: bounds = [u0, u1, u2, u3, top]. Top tier's lower bound is inclusive."""
    if magi >= bounds[4]:
        return 5
    for k in range(4):
        if magi <= bounds[k]:
            return k
    return 4


def compute_return(Y, filing, n65, lines, itemized_in, gov_pension_by_person, sc, prm, flags):
    """Sections 9 and 10 for one return. `lines` holds the income figures; returns a dict of results."""
    sw = sc["switches"]
    agi_ex_ss = (lines["wages"] + lines["interest_taxable"] + lines["ordinary_dividends"] + lines["line4b"]
                 + lines["line5b"] + lines["line7"] + lines["rental"])                         # 9.2
    tss = taxable_social_security(lines["ss_total"], agi_ex_ss, lines["interest_tax_exempt"], filing, prm)
    agi = agi_ex_ss + tss                                                                         # 9.1 line 11
    senior = senior_deduction(Y, agi, n65, filing, prm)                                           # 9.10
    # 9.7 standard deduction
    std = (prm.get("standard_deduction", Y)[filing]
           + prm.get("additional_std_65", Y)["married" if filing == "mfj" else "unmarried"] * n65)
    charity = itemized_in["charity_cash"]
    nonitem = (min(charity, prm.const("nonitemizer_charitable_cap")[filing])
               if Y >= prm.const("nonitemizer_charitable_first_year") else 0.0)
    # 9.8 pieces that do not depend on the state tax
    medical_fed = max0(itemized_in["medical"] - prm.const("medical_floor_rate") * agi)
    if Y >= prm.const("charitable_floor_first_year"):
        ch_base = max0(charity - prm.const("charitable_floor_rate") * agi)
    else:
        ch_base = charity
    ceiling = prm.const("charitable_cash_ceiling_rate") * agi
    charity_item = min(ch_base, ceiling)
    if ch_base > ceiling + 1e-9:
        flags.add("charitable_excess")
    salt_cap = salt_cap_amount(Y, agi, prm)
    limit_on = Y >= prm.const("itemized_limit_first_year")
    b37 = prm.get("bracket37_start", Y)[filing]
    rate68 = prm.const("itemized_limit_rate")

    def fed_salt(T):
        return min(T + itemized_in["salt_other"], salt_cap)

    def fed_itemized(T):
        pre = medical_fed + fed_salt(T) + itemized_in["mortgage_interest"] + charity_item
        red = itemized_limit_reduction(pre, agi - senior, b37, rate68) if limit_on else 0.0
        return pre - red

    # Section 10 Arizona
    az = None
    T = 0.0
    if sc["state"] == "AZ":
        additions = lines["interest_tax_exempt"] * (1 - sc["az_muni_in_state_share"])
        ltcg_sub = (prm.const("az_ltcg_subtraction_rate") * max0(lines["line7"])
                    if sw["az_ltcg_acquired_after_2011"] else 0.0)
        gov = (sum(min(v, prm.const("az_gov_pension_max")) for v in gov_pension_by_person.values())
               if sw["az_pension_is_government"] else 0.0)
        senior_sub = senior if sw["az_senior_subtraction"] else 0.0
        exemptions = prm.const("az_age65_exemption") * n65
        az_agi = max0(agi + additions - tss - ltcg_sub - gov - senior_sub - exemptions)
        az_std = prm.get("az_standard_deduction", Y)[filing]
        if Y >= prm.const("az_charitable_new_form_first_year"):
            az_inc = min(charity, prm.const("az_charitable_std_increase_cap")[filing])
        else:
            az_inc = prm.get("az_charitable_std_increase_rate", Y) * charity_item
        az_std_total = az_std + az_inc

        def az_parts(Tx):
            fs = fed_salt(Tx)
            az_taxes = min(fs, prm.const("az_salt_cap")) if Y >= prm.const("az_salt_cap_first_year") else fs
            pre = itemized_in["medical"] + az_taxes + itemized_in["mortgage_interest"] + charity_item
            red = itemized_limit_reduction(pre, agi - senior, b37, rate68) if limit_on else 0.0
            item = pre - red
            ded = max(az_std_total, item)
            return prm.get("az_rate", Y) * max0(az_agi - ded), item, ded

        T = az_parts(0.0)[0]
        for _ in range(200):                                   # 10.3 fixed point
            T_next = az_parts(T)[0]
            if abs(T_next - T) < 0.001:
                T = T_next
                break
            T = T_next
        _, az_item, az_ded = az_parts(T)
        az = {"agi": az_agi, "deduction": az_ded, "itemized": az_item, "standard": az_std_total,
              "taxable_income": max0(az_agi - az_ded), "tax": T}

    itemized = fed_itemized(T)
    if itemized > std + nonitem:                               # 9.9 ties go to the standard deduction
        ded_type, deduction = "itemized", itemized
    else:
        ded_type, deduction = "standard", std + nonitem
    TI = max0(agi - deduction - senior)                        # 9.11
    QD = lines["qualified_dividends"]
    CG = max0(lines["line7"])
    reg = regular_tax(Y, filing, TI, QD, CG, prm)
    # 9.12 NIIT
    nii = max0(lines["interest_taxable"] + lines["ordinary_dividends"] + lines["line7"] + lines["rental"]
               + (lines["annuity_taxable"] if sw["annuity_is_nii"] else 0.0))
    niit_p = prm.const("niit")
    niit = niit_p["rate"] * min(nii, max0(agi - niit_p["threshold"][filing]))
    add10 = prm.const("early_withdrawal_rate") * lines["penalty_base"]
    return {"agi_ex_ss": agi_ex_ss, "taxable_ss": tss, "agi": agi,
            "magi_irmaa": agi + lines["interest_tax_exempt"],
            "deduction_type": ded_type, "deduction": deduction, "senior_deduction": senior,
            "taxable_income": TI, "regular_tax": reg, "niit": niit, "additional_10pct": add10,
            "federal_tax": reg + niit + add10, "state_tax": T, "az": az}


# =========================================================================================================
# Section 12 — Medicare premiums
# =========================================================================================================
def irmaa_lookup(Y, returns, prior_magi, first_year, lookback):
    """12.2: (magi, filing, lookback_year, assumed)."""
    L = Y - lookback
    if L < first_year:
        pm = prior_magi.get(L)
        if pm is None:
            return None, None, L, True
        return float(pm["magi"]), pm["filing"], L, False
    magi, filing = returns[L]
    return magi, filing, L, False


def medicare_for_year(sc, Y, returns, prm, flags):
    """12.1-12.4: {pid: {tier, premium, lookback_year}} for living people with Medicare months this year."""
    out = {}
    enrolled = [pid for pid in sc["pids"]
                if alive_in(sc, pid, Y) and medicare_months(sc["people"][pid], Y) > 0]
    if not enrolled:
        return out
    magi, filing, L, assumed = irmaa_lookup(Y, returns, sc["prior_magi"], sc["first_year"],
                                            prm.const("irmaa_lookback_years"))
    if assumed:
        flags.add("irmaa_lookback_assumed")
        tier = 0
    else:
        tier = irmaa_tier(magi, prm.get("irmaa_bounds", Y)[filing])
    monthly = (prm.get("part_b_monthly", Y)[tier] + prm.get("part_d_irmaa_monthly", Y)[tier]
               + sc["part_d_base_monthly"])
    for pid in enrolled:
        out[pid] = {"tier": tier, "premium": medicare_months(sc["people"][pid], Y) * monthly,
                    "lookback_year": L}
    return out


# =========================================================================================================
# State set-up
# =========================================================================================================
def init_state(sc):
    st = {"acc": {}, "order": [], "basis8606": {pid: 0.0 for pid in sc["pids"]}, "roth": {},
          "carry": sc["prior_cap_loss"], "deferred": {}}
    for pid in sc["pids"]:
        st["roth"][pid] = {"first": None, "contrib": 0.0, "layers": []}
    for a in sc["accounts"]:
        acc = {"id": a["id"], "owner": a["owner"], "type": a["type"], "bal": a["bal"], "basis": a["basis"],
               "dy": a["dy"], "qs": a["qs"], "sched": None, "titling": a["titling"]}
        t = a["type"]
        if t == "traditional_ira":
            st["basis8606"][a["owner"]] += a["after_tax_basis"]                 # 1.2 reading
        elif t == "roth_ira":
            led = st["roth"][a["owner"]]
            fry = a["first_roth_year"]
            if fry is None:
                fry = sc["first_year"] - 5   # not given: treated as a satisfied five-year period (NOTES)
            led["first"] = fry if led["first"] is None else min(led["first"], int(fry))
            led["contrib"] += a["contribution_basis"]
            for L in a["conversion_layers"]:
                led["layers"].append([int(L["year"]), float(L.get("taxable_amount", 0.0)),
                                      float(L.get("nontaxable_amount", 0.0))])
        elif t in ("inherited_ira", "inherited_roth_ira"):
            holder = sc["people"][a["owner"]]
            acc["sched"] = inherited_setup(a, holder, sc["switches"])
            if t == "inherited_roth_ira":
                fry = a["first_roth_year"]
                acc["roth_first"] = int(fry) if fry is not None else sc["first_year"] - 5
                acc["roth_ledger"] = {"contrib": a["contribution_basis"], "layers": []}
        if t in ("taxable", "cash") and a["owner"] == "joint":
            acc["owner"] = "joint"
        st["acc"][a["id"]] = acc
        st["order"].append(a["id"])
    return st


def new_account_id(st, base):
    if base not in st["acc"]:
        return base
    k = 2
    while "%s_%d" % (base, k) in st["acc"]:
        k += 1
    return "%s_%d" % (base, k)


def owner_person(sc, acc):
    """The person whose age tests apply to an account ('joint' = first living person)."""
    return acc["owner"] if acc["owner"] != "joint" else sc["pids"][0]


# =========================================================================================================
# Sections 4, 7, 8, 9, 10 — one evaluation of the year for a given spending withdrawal W
# =========================================================================================================
class YearCtx:
    pass


def evaluate_year(st0, Y, W, ctx):
    """Run steps 5-6 (growth, Dec 31 transactions a-g) and the tax computation with spending gap W.
    Works on a copy of the opening state; returns a result dict holding the new state."""
    sc, prm = ctx.sc, ctx.prm
    people = sc["people"]
    st = copy.deepcopy(st0)
    acc, ids = st["acc"], st["order"]
    ret = sc["return"]
    flags = set()
    r = {k: {} for k in ("rmd", "qcd", "conversion", "distributions", "sales")}
    for i in ids:
        r["distributions"][i] = 0.0
    tr_noconv = {pid: 0.0 for pid in sc["pids"]}    # Form 8606 line 7 per person
    tr_conv = {pid: 0.0 for pid in sc["pids"]}      # Form 8606 line 8 per person
    k401 = {pid: 0.0 for pid in sc["pids"]}         # 401(k) distributions (not conversions) per person
    k401_conv = {pid: 0.0 for pid in sc["pids"]}
    inh_taxable = 0.0
    roth_taxable = 0.0
    penalty_base = 0.0
    realized = 0.0
    rmd_cash = 0.0
    plan_cash = 0.0

    # ---- step 4: RMDs from opening balances (6, 6A) -------------------------------------------------------
    B0 = {i: acc[i]["bal"] for i in ids}
    grown = {i: B0[i] * (1 + ret) for i in ids}
    rmd_req = {}
    new_deferred = dict(st["deferred"])
    for i in ids:
        a = acc[i]
        t = a["type"]
        if t in ("traditional_ira", "401k"):
            req = owner_rmd(sc, a, Y, B0[i], grown[i])
            o = people[a["owner"]]
            fry = first_rmd_year(o["born"], o["born_month"])
            if sc["switches"]["defer_first_rmd"]:
                if Y == fry and sc["deaths"].get(a["owner"]) != Y:
                    new_deferred[i] = req                 # 6.1 switch: taken next year on its own balance
                    req = 0.0
                elif i in new_deferred:
                    req = min(req + new_deferred.pop(i), grown[i])
            rmd_req[i] = req
            r["rmd"][i] = req
        elif t in ("inherited_ira", "inherited_roth_ira"):
            rmd_req[i] = inherited_rmd(a["sched"], Y, B0[i], grown[i], prm)
            r["rmd"][i] = rmd_req[i]
    st["deferred"] = new_deferred

    # ---- step 5: growth and investment income (Section 4) -----------------------------------------------
    dividends = qualified = cash_interest = 0.0
    for i in ids:
        a = acc[i]
        a["bal"] = grown[i]
        if a["type"] == "taxable":
            d = a["dy"] * B0[i]
            dividends += d
            qualified += a["qs"] * d
            a["basis"] += d
        elif a["type"] == "cash":
            cash_interest += ret * B0[i]

    roth_queue = []   # all roth_ira withdrawals this year, ordered after this year's conversion layers exist

    def take(i, x):
        """Distribute x from account i (a distribution, a plan withdrawal or a spending withdrawal)."""
        nonlocal inh_taxable, roth_taxable, penalty_base, realized
        a = acc[i]
        x = min(x, a["bal"])
        if x <= 0:
            return 0.0
        r["distributions"][i] += x
        t = a["type"]
        if t == "taxable":
            realized += sell_taxable(a, x)
            r["sales"][i] = r["sales"].get(i, 0.0) + x
            return x
        a["bal"] -= x
        if t == "traditional_ira":
            tr_noconv[a["owner"]] += x
        elif t == "401k":
            k401[a["owner"]] += x
            if not over_59h(people[a["owner"]], Y):
                penalty_base += x                        # 7.9
        elif t == "inherited_ira":
            inh_taxable += x                             # 7.8; never the 10% tax (6A.7)
        elif t == "inherited_roth_ira":
            roth_distribution(i, x)                      # 6A.8: own ledger, no same-year conversions
        elif t == "roth_ira":
            # 7.5 v1.1 "same-year conversions count" (Reg. §1.408A-6 Q&A-9(a), (c)): the year's distributions are
            # aggregated and ordered at year end, after this year's conversions are added as a layer for Y.
            roth_queue.append((i, x))
        return x

    def roth_distribution(i, x):
        nonlocal roth_taxable, penalty_base
        a = acc[i]
        if a["type"] == "inherited_roth_ira":            # 6A.8
            qualified_d = Y >= a["roth_first"] + prm.const("roth_five_year")
            tx, pen = roth_take(a["roth_ledger"], x, Y, qualified_d, False, True)
        else:                                            # 7.5
            o = people[a["owner"]]
            led = st["roth"][a["owner"]]
            five = led["first"] is not None and Y >= led["first"] + prm.const("roth_five_year")
            qualified_d = five and over_59h(o, Y)
            tx, pen = roth_take(led, x, Y, qualified_d, not over_59h(o, Y), False)
        roth_taxable += tx
        penalty_base += pen

    acts = ctx.actions

    # ---- step 6a: QCDs (7.2) ---------------------------------------------------------------------------
    qcd_used = {pid: 0.0 for pid in sc["pids"]}
    qcd_limit = None
    for act in acts:
        if act["type"] != "qcd":
            continue
        i = act["from"]
        a = acc.get(i)
        if a is None or a["type"] not in ("traditional_ira", "inherited_ira") or \
                not over_70h(people[a["owner"]], Y):
            flags.add("qcd_void")
            continue
        if qcd_limit is None:
            qcd_limit = prm.get("qcd_limit", Y)
        amt = float(act["amount"])
        x = max0(min(amt, qcd_limit - qcd_used[a["owner"]], a["bal"]))
        if x < amt - 1e-9:
            flags.add("action_clamped")
        a["bal"] -= x
        r["distributions"][i] += x
        r["qcd"][i] = r["qcd"].get(i, 0.0) + x
        qcd_used[a["owner"]] += x

    # ---- step 6b: remaining RMDs (6.3, 6A.7) ------------------------------------------------------------
    for pid in sc["pids"]:
        own_iras = [i for i in ids if acc[i]["type"] == "traditional_ira" and acc[i]["owner"] == pid]
        need = max0(sum(rmd_req.get(i, 0.0) for i in own_iras) - sum(r["qcd"].get(i, 0.0) for i in own_iras))
        tot = sum(acc[i]["bal"] for i in own_iras)
        if need > 0 and tot > 0:
            need = min(need, tot)
            for i in own_iras:
                rmd_cash += take(i, need * acc[i]["bal"] / tot if tot else 0.0)
    for i in ids:
        a = acc[i]
        if a["type"] == "401k":
            rmd_cash += take(i, rmd_req.get(i, 0.0))
        elif a["type"] in ("inherited_ira", "inherited_roth_ira"):
            rmd_cash += take(i, max0(rmd_req.get(i, 0.0) - r["qcd"].get(i, 0.0)))

    # ---- step 6c: plan withdrawals (7.4) ----------------------------------------------------------------
    for act in acts:
        if act["type"] != "withdrawal":
            continue
        i = act["from"]
        if i not in acc:
            flags.add("action_void")
            continue
        amt = float(act["amount"])
        if amt > acc[i]["bal"] + 1e-9:
            flags.add("action_clamped")
        plan_cash += take(i, amt)

    # ---- step 6d: Roth conversions (7.4) ----------------------------------------------------------------
    for act in acts:
        if act["type"] != "roth_conversion":
            continue
        i = act["from"]
        a = acc.get(i)
        if a is None:
            flags.add("action_void")
            continue
        amt = float(act["amount"])
        x = max0(min(amt, a["bal"]))
        if x < amt - 1e-9:
            flags.add("action_clamped")
        if x <= 0:
            continue
        o = a["owner"]
        a["bal"] -= x
        r["distributions"][i] += x
        r["conversion"][i] = r["conversion"].get(i, 0.0) + x
        if a["type"] == "traditional_ira":
            tr_conv[o] += x
        else:
            k401_conv[o] += x
        dest = next((j for j in ids if acc[j]["type"] == "roth_ira" and acc[j]["owner"] == o), None)
        if dest is None:
            dest = new_account_id(st, "roth_ira_%s" % o)
            acc[dest] = {"id": dest, "owner": o, "type": "roth_ira", "bal": 0.0, "basis": 0.0, "dy": 0.0,
                         "qs": 0.0, "sched": None}
            ids.append(dest)
            r["distributions"][dest] = 0.0
        led = st["roth"][o]
        led["first"] = Y if led["first"] is None else min(led["first"], Y)   # Reg. §1.408A-6 Q&A-2
        acc[dest]["bal"] += x

    # ---- step 6e: gain harvesting (7.6) -----------------------------------------------------------------
    for act in acts:
        if act["type"] != "harvest_gains":
            continue
        amt = float(act["amount"])
        tax_ids = [i for i in ids if acc[i]["type"] == "taxable"]
        unreal = {i: max0(acc[i]["bal"] - acc[i]["basis"]) for i in tax_ids}
        tot = sum(unreal.values())
        G = min(amt, tot)
        if G < amt - 1e-9:
            flags.add("action_clamped")
        if G > 0:
            for i in tax_ids:
                g = G * unreal[i] / tot
                acc[i]["basis"] += g
                realized += g

    # ---- step 6f: spending withdrawals (8.2) ------------------------------------------------------------
    pools = [("cash",), ("taxable",), PRETAX_TYPES, ROTH_TYPES]
    w_max = sum(acc[i]["bal"] for i in ids)
    remaining = min(W, w_max)
    spend = {}
    for types in pools:
        if remaining <= 0:
            break
        members = [i for i in ids if acc[i]["type"] in types and acc[i]["bal"] > 0]
        tot = sum(acc[i]["bal"] for i in members)
        if tot <= 0:
            continue
        x = min(remaining, tot)
        shares = [(i, x * acc[i]["bal"] / tot) for i in members]
        for i, s in shares:
            got = take(i, s)
            spend[i] = got
        remaining -= x

    # ---- Form 8606 per person (9.5) and the Roth ledger's new layers (7.4, 11) ---------------------------
    line4b_trad = 0.0
    f8606 = {}
    for pid in sc["pids"]:
        line6 = sum(acc[i]["bal"] for i in ids if acc[i]["type"] == "traditional_ira" and acc[i]["owner"] == pid)
        f = form8606(st["basis8606"][pid], line6, tr_noconv[pid], tr_conv[pid],
                     sc["switches"]["round_8606_ratio_3dp"])
        f8606[pid] = f
        line4b_trad += f["line15c"] + f["line18"]
        st["basis8606"][pid] = f["line14"]
        if not over_59h(people[pid], Y):
            penalty_base += f["line15c"]                 # 7.9 (conversions are exempt)
        if tr_conv[pid] > 0 or k401_conv[pid] > 0:
            st["roth"][pid]["layers"].append([Y, f["line18"] + k401_conv[pid], f["line11"]])
    for i, x in roth_queue:
        roth_distribution(i, x)

    # ---- capital gains, line 7 (9.1; Schedule D) --------------------------------------------------------
    net_gain = realized - st["carry"]
    limit = prm.const("capital_loss_limit")[ctx.filing]
    if net_gain >= 0:
        line7, carry_out = net_gain, 0.0
    else:
        line7 = -min(-net_gain, limit)
        carry_out = -net_gain + line7
    st["carry"] = carry_out

    # ---- the return ------------------------------------------------------------------------------------
    inc = ctx.income
    lines = {
        "wages": inc["wages"], "interest_taxable": inc["interest_taxable"] + cash_interest,
        "interest_tax_exempt": inc["interest_tax_exempt"], "ordinary_dividends": dividends,
        "qualified_dividends": qualified,
        "line4b": line4b_trad + inh_taxable + roth_taxable,
        "line5b": inc["pension"] + inc["annuity_taxable"] + sum(k401.values()) + sum(k401_conv.values()),
        "line7": line7, "rental": inc["rental"], "annuity_taxable": inc["annuity_taxable"],
        "ss_total": ctx.ss_total, "penalty_base": penalty_base,
    }
    tax = compute_return(Y, ctx.filing, ctx.n65, lines, ctx.itemized, ctx.gov_pension, sc, prm, flags)

    # ---- 8.1 cash flow -----------------------------------------------------------------------------------
    inflows = (inc["wages"] + inc["pension"] + inc["annuity_taxable"] + inc["interest_taxable"]
               + inc["interest_tax_exempt"] + inc["rental"] + ctx.ss_total + rmd_cash + plan_cash)
    spent_w = sum(spend.values())
    net = inflows + spent_w - ctx.need - tax["federal_tax"] - tax["state_tax"] - ctx.medicare_total

    return {"state": st, "net": net, "w_max": w_max, "w": spent_w, "tax": tax, "lines": lines, "r": r,
            "flags": flags, "f8606": f8606, "spend": spend}


def deposit_surplus(res, sc, amount):
    """8.3 / step 6g: deposit a surplus to cash (creating a cash account if needed)."""
    st = res["state"]
    acc, ids = st["acc"], st["order"]
    cash = next((i for i in ids if acc[i]["type"] == "cash"), None)
    if cash is None:
        if amount < 0.01:
            return
        cash = new_account_id(st, "cash")
        owner = "joint" if sc["filing"] == "mfj" else sc["pids"][0]
        acc[cash] = {"id": cash, "owner": owner, "type": "cash", "bal": 0.0, "basis": 0.0, "dy": 0.0,
                     "qs": 0.0, "sched": None}
        ids.append(cash)
        res["r"]["distributions"][cash] = 0.0
    acc[cash]["bal"] += amount


def solve_year(st, Y, ctx):
    """8.3: unique W with net(W) >= 0 by bisection."""
    r0 = evaluate_year(st, Y, 0.0, ctx)
    if r0["net"] >= 0:
        deposit_surplus(r0, ctx.sc, r0["net"])
        r0["unfunded"] = 0.0
        return r0
    w_max = r0["w_max"]
    rmax = evaluate_year(st, Y, w_max, ctx)
    if rmax["net"] < 0:
        rmax["unfunded"] = -rmax["net"]
        return rmax
    lo, hi = 0.0, w_max
    while hi - lo >= 0.005:
        mid = (lo + hi) / 2
        if evaluate_year(st, Y, mid, ctx)["net"] >= 0:
            hi = mid
        else:
            lo = mid
    res = evaluate_year(st, Y, hi, ctx)
    if res["net"] > 0:
        deposit_surplus(res, ctx.sc, res["net"])
    res["unfunded"] = 0.0
    return res


# =========================================================================================================
# Section 3.3 — death transitions
# =========================================================================================================
def apply_death(st, sc, d, s):
    """Returns the set of flags raised by the transition."""
    sw = sc["switches"]
    flags = set()
    for i in st["order"]:
        a = st["acc"][i]
        t = a["type"]
        if a["owner"] == d:
            a["owner"] = s
            if t == "401k" and sw["spouse_401k_to_ira"]:
                a["type"] = "traditional_ira"                          # step 2
            elif t in ("inherited_ira", "inherited_roth_ira"):         # step 4; 6A.6
                sched = a["sched"]
                D_b = sc["deaths"][d]
                if sched["edb_life_expectancy"]:                       # v1.2: Reg. §1.401(a)(9)-5(e)(3)-(4)
                    sched["deadline"] = (D_b + 10 if sched["deadline"] is None
                                         else min(sched["deadline"], D_b + 10))
                if sched["div"] in ("s", "max_s_o") and sched["frozen"] is None:
                    sched["frozen"] = D_b
            elif t == "taxable":
                a["basis"] = a["bal"]                                  # step 5: full step-up
        elif a["owner"] == "joint":
            if t == "taxable":                                         # step 5 (v1.2): by titling
                titling = a.get("titling")
                if titling is None:
                    flags.add("stepup_titling_assumed")
                    titling = "community" if sw["community_property"] else "jtwros"
                if titling in ("community", "community_with_survivorship"):
                    a["basis"] = a["bal"]                              # IRC §1014(b)(6)
                else:
                    a["basis"] = 0.5 * a["basis"] + 0.5 * a["bal"]     # IRC §2040(b)
            a["owner"] = s
    st["basis8606"][s] += st["basis8606"][d]                           # step 1
    st["basis8606"][d] = 0.0
    ld, ls = st["roth"][d], st["roth"][s]                              # step 3
    if ld["first"] is not None:
        ls["first"] = ld["first"] if ls["first"] is None else min(ls["first"], ld["first"])
    ls["contrib"] += ld["contrib"]
    ls["layers"].extend(ld["layers"])
    st["roth"][d] = {"first": None, "contrib": 0.0, "layers": []}
    return flags


# =========================================================================================================
# Plan simulation and outputs (Sections 2, 13, 15)
# =========================================================================================================
def income_for_year(sc, Y):
    """1.3: income items by type, and pension by person (for the Arizona government-pension subtraction)."""
    tot = {t: 0.0 for t in INCOME_TYPES}
    pension_by = {}
    for it in sc["income"]:
        start = it["start_year"] if it["start_year"] is not None else -10 ** 6
        end = it["end_year"] if it["end_year"] is not None else 10 ** 6
        if not (start <= Y <= end):
            continue
        o = it["owner"]
        if o in sc["deaths"] and Y > sc["deaths"][o] and it["type"] not in SURVIVING_INCOME:
            continue
        amt = it["annual"] * (1 + it["cola"]) ** (Y - max(start, sc["first_year"]))
        tot[it["type"]] += amt
        if it["type"] == "pension":
            pension_by[o] = pension_by.get(o, 0.0) + amt
    return tot, pension_by


def run_plan(sc, plan, prm):
    validate_plan(sc, plan)
    prm.reset_tracking()
    first, last = sc["first_year"], sc["last_year"]
    years = list(range(first, last + 1))
    ss = ss_schedule(sc, plan, prm, years)
    st = init_state(sc)
    returns = {}
    rows = []
    first_death = min(sc["deaths"].values()) if sc["deaths"] else None
    for Y in years:
        living = [pid for pid in sc["pids"] if alive_in(sc, pid, Y)]
        if not living:
            break
        filing = "mfj" if (sc["filing"] == "mfj" and len(living) == 2) else "single"     # 3.2
        flags = set()
        ctx = YearCtx()
        ctx.sc, ctx.prm, ctx.filing = sc, prm, filing
        ctx.n65 = sum(1 for pid in living if is65(sc["people"][pid], Y))
        ctx.actions = [a for a in plan.get("actions", [])
                       if a["type"] != "claim_social_security" and Y in [int(y) for y in a.get("years", [])]]
        ctx.income, ctx.gov_pension = income_for_year(sc, Y)
        ctx.ss_total = sum(ss[pid][Y] for pid in sc["pids"])
        infl = (1 + sc["inflation"]) ** (Y - first)
        need = sc["spending_need"] * infl
        if first_death is not None and Y > first_death:
            need *= sc["survivor_spending_ratio"]
        ctx.need = need
        ctx.itemized = {k: v * infl for k, v in sc["itemized"].items()}
        med = medicare_for_year(sc, Y, returns, prm, flags)                                 # 12
        ctx.medicare_total = sum(m["premium"] for m in med.values())
        res = solve_year(st, Y, ctx)                                                        # 6, 8, 9, 10
        st = res["state"]
        tax = res["tax"]
        returns[Y] = (tax["magi_irmaa"], filing)
        flags |= res["flags"]
        lines = res["lines"]
        acc = st["acc"]
        row = {
            "year": Y, "filing": filing,
            "alive": {pid: alive_in(sc, pid, Y) for pid in sc["pids"]},
            "age": {pid: age(sc["people"][pid], Y) for pid in living},
            "projected": Y in prm.projected_years,
            "social_security": {pid: ss[pid][Y] for pid in living},
            "rmd": {i: res["r"]["rmd"].get(i, 0.0) for i in st["order"]
                    if acc[i]["type"] in ("traditional_ira", "401k", "inherited_ira", "inherited_roth_ira")},
            "qcd": {i: res["r"]["qcd"].get(i, 0.0) for i in st["order"]
                    if acc[i]["type"] in ("traditional_ira", "inherited_ira")},
            "conversion": {i: res["r"]["conversion"].get(i, 0.0) for i in st["order"]
                           if acc[i]["type"] in ("traditional_ira", "401k")},
            "distributions": {i: res["r"]["distributions"].get(i, 0.0) for i in st["order"]},
            "sales": {i: res["r"]["sales"].get(i, 0.0) for i in st["order"] if acc[i]["type"] == "taxable"},
            "income": {
                "wages": ctx.income["wages"], "pension": ctx.income["pension"],
                "annuity_taxable": ctx.income["annuity_taxable"],
                "interest_taxable": lines["interest_taxable"],
                "interest_tax_exempt": lines["interest_tax_exempt"], "rental": lines["rental"],
                "ordinary_dividends": lines["ordinary_dividends"],
                "qualified_dividends": lines["qualified_dividends"], "capital_gain": lines["line7"],
                "ira_taxable": lines["line4b"] + lines["line5b"] - ctx.income["pension"]
                - ctx.income["annuity_taxable"],
            },
            "taxable_ss": tax["taxable_ss"], "agi": tax["agi"], "magi_irmaa": tax["magi_irmaa"],
            "deduction_type": tax["deduction_type"], "deduction": tax["deduction"],
            "senior_deduction": tax["senior_deduction"], "taxable_income": tax["taxable_income"],
            "regular_tax": tax["regular_tax"], "niit": tax["niit"], "additional_10pct": tax["additional_10pct"],
            "federal_tax": tax["federal_tax"], "state_tax": tax["state_tax"],
            "medicare": med, "medicare_total": ctx.medicare_total,
            "balances": {i: acc[i]["bal"] for i in st["order"]},
            "basis8606": {pid: st["basis8606"][pid] for pid in living},
            "unfunded_spending": res["unfunded"],
            "flags": sorted(flags),
        }
        rows.append(row)
        # step 9: death transitions (3.3)
        dying = [pid for pid in living if sc["deaths"].get(pid) == Y]
        survivors = [pid for pid in living if pid not in dying]
        if dying and survivors:
            for d in dying:
                death_flags = apply_death(st, sc, d, survivors[0])
                row["flags"] = sorted(set(row["flags"]) | death_flags)   # reported in the year of death
        if not survivors:
            break                                                                           # 13
    return {"years": rows, "totals": totals(sc, rows, st)}


def totals(sc, rows, st):
    """15.2-15.3."""
    first, infl, h = sc["first_year"], sc["inflation"], sc["heirs_tax_rate"]
    t = {"lifetime_tax": 0.0, "lifetime_tax_real": 0.0, "lifetime_medicare": 0.0, "lifetime_medicare_real": 0.0}
    for row in rows:
        d = (1 + infl) ** (row["year"] - first)
        tx = row["federal_tax"] + row["state_tax"]
        t["lifetime_tax"] += tx
        t["lifetime_tax_real"] += tx / d
        t["lifetime_medicare"] += row["medicare_total"]
        t["lifetime_medicare_real"] += row["medicare_total"] / d
    pretax = sum(a["bal"] for a in st["acc"].values() if a["type"] in PRETAX_TYPES)
    other = sum(a["bal"] for a in st["acc"].values() if a["type"] not in PRETAX_TYPES)
    if sc["switches"]["heirs_credit_8606_basis"]:
        b = min(pretax, sum(st["basis8606"].values()))
        ew = (pretax - b) * (1 - h) + b + other
    else:
        ew = pretax * (1 - h) + other
    last = rows[-1]["year"] if rows else first
    t["end_wealth"] = ew
    t["end_wealth_real"] = ew / (1 + infl) ** (last - first)
    return t


def round_cents(x):
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, float):
        return round(x + 0.0, 2)
    if isinstance(x, dict):
        return {k: round_cents(v) for k, v in x.items()}
    if isinstance(x, list):
        return [round_cents(v) for v in x]
    return x


def run(raw, prm=None):
    sc = normalize(raw)
    if prm is None:
        prm = Params(inflation=sc["inflation"], chained_cpi_gap=sc["chained_cpi_gap"],
                     cola=None if sc["cola"] is None else float(sc["cola"]),
                     medicare_growth=None if sc["medicare_growth"] is None else float(sc["medicare_growth"]))
    out = {"plans": {}}
    for plan in raw["plans"]:
        out["plans"][plan["name"]] = run_plan(sc, plan, prm)
    return round_cents(out)


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: engine.py scenario.json\n")
        return 2
    with open(argv[1]) as f:
        raw = json.load(f)
    try:
        out = run(raw)
    except InputError as e:
        sys.stderr.write("input error: %s\n" % e)
        return 1
    json.dump(out, sys.stdout, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
