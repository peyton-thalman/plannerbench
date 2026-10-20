"""The statistics behind every published number, so no score is reported without its uncertainty.

Accuracy is measured per question: with repeated runs, a question counts as the share of its runs that were right,
so asking the same question three times never looks like three independent questions.
"""
import math
from collections import defaultdict

Z = 1.96  # 95% intervals


def wilson(k, n):
    """95% Wilson score interval for k successes in n trials; stays inside [0, 1] and behaves at 0% and 100%."""
    if n == 0:
        return None, None
    p = k / n
    centre = (p + Z * Z / (2 * n)) / (1 + Z * Z / n)
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / (1 + Z * Z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def per_question(rows):
    """(questions, effective correct): each question's runs averaged into one score."""
    runs = defaultdict(list)
    for r in rows:
        runs[r["id"]].append(r["bucket"] == "correct")
    return len(runs), sum(sum(v) / len(v) for v in runs.values())


def accuracy(rows):
    """{"accuracy", "lo", "hi", "questions"} for a set of graded replies, errors already removed."""
    n, k = per_question(rows)
    if not n:
        return {"accuracy": None, "lo": None, "hi": None, "questions": 0}
    lo, hi = wilson(k, n)
    return {"accuracy": round(k / n, 4), "lo": round(lo, 4), "hi": round(hi, 4), "questions": n}


def mcnemar(pairs):
    """Exact two-sided McNemar p-value for paired right/wrong outcomes [(a_correct, b_correct), ...].

    Used when the same questions are asked two ways (with and without a rule, or two models), where only the
    questions that flip carry information.
    """
    b = sum(1 for x, y in pairs if x and not y)
    c = sum(1 for x, y in pairs if y and not x)
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)
