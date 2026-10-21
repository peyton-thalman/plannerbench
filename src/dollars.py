"""What a wrong answer costs the client, in dollars a year, not just whether it was wrong.

Accuracy counts a Medicare premium ten cents off the same as an RMD $9,000 too high. A planner wouldn't, so every
numeric reply also gets "dollars off": |answer - key|, put on a yearly basis (monthly Social Security and Part B
answers times 12). A right answer is $0 off. A miss of $1,000 a year or more is "material": big enough that a client
acting on it would notice, and often big enough to change what they do.

Only replies that gave a number count here (a truncated or missing reply has no dollar figure; accuracy already
counts it as not right). Compliance tasks have no dollar answer and are left out.
"""
import random
import statistics
from collections import defaultdict

from stats import wilson

PER_YEAR = {"ss_claim": 12, "irmaa": 12}  # monthly answers
NO_DOLLARS = {"rollover_flags", "breakpoint", "comms_review"}
MATERIAL = 1000  # dollars a year


def off(g):
    """Dollars a year this reply is off from the key; 0 when graded right."""
    return 0.0 if g["bucket"] == "correct" else abs(g["got"] - g["key"]) * PER_YEAR.get(g["task"], 1)


def priced(rows):
    return [g for g in rows if g["task"] not in NO_DOLLARS and g["bucket"] in ("correct", "wrong")]


def per_question(rows, f):
    """Each question's runs averaged into one value, as stats.per_question does for accuracy."""
    runs = defaultdict(list)
    for g in rows:
        runs[g["id"]].append(f(g))
    return [sum(v) / len(v) for v in runs.values()]


def mean_interval(xs, draws=2000):
    """Mean and a 95% bootstrap interval over questions; seeded so ./reproduce.sh gets the same digits."""
    rng = random.Random(0)
    means = sorted(statistics.fmean(rng.choices(xs, k=len(xs))) for _ in range(draws))
    return statistics.fmean(xs), means[int(0.025 * draws)], means[int(0.975 * draws) - 1]


def summary(rows):
    rows = priced(rows)
    if not rows:
        return None
    dollars = per_question(rows, off)
    mean, lo, hi = mean_interval(dollars)
    material = per_question(rows, lambda g: off(g) >= MATERIAL)
    m_lo, m_hi = wilson(sum(material), len(material))
    misses = [off(g) for g in rows if g["bucket"] == "wrong"]
    return {"questions": len(dollars), "dollars_off_per_question": round(mean, 2), "dollars_lo": round(lo, 2), "dollars_hi": round(hi, 2),
            "material_rate": round(sum(material) / len(material), 4), "material_lo": round(m_lo, 4), "material_hi": round(m_hi, 4),
            "misses": len(misses), "median_miss": round(statistics.median(misses), 2) if misses else None,
            "worst_miss": round(max(misses), 2) if misses else None}


def by_mistake(rows):
    """How big each named mistake is, across models: the mistakes to fix first are common and large."""
    sizes = defaultdict(list)
    for g in priced(rows):
        if g["bucket"] == "wrong":
            sizes[g.get("mistake") or "unexplained"].append(off(g))
    return [{"mistake": k, "count": len(v), "median_off": round(statistics.median(v), 2), "total_off": round(sum(v), 2),
             "material": sum(x >= MATERIAL for x in v)} for k, v in sorted(sizes.items(), key=lambda kv: -sum(kv[1]))]
