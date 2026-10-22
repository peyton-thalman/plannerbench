"""The MoneyGuide planning tools, reached over MCP (Model Context Protocol) the way any AI app would reach them.

The tool server lives with the engine (~/moneyguide/mcp/server.ts; build it once with `npm run mcp:build` there).
This file starts it, speaks MCP to it over stdin/stdout, and offers:

  PlanningTools().list()            the tool definitions, for an API request's `tools`
  PlanningTools().call(name, args)  one tool call, returning the JSON the server sent back
  oracle(tools, case)               the answer a perfect tool user gives, composed from tool calls only

oracle() is the "tools are enough" check (checks/tools_check.py) and the stand-in model for `run_models.py --fake
--tools`. It reads the case's inputs, so it shows what the tools can do, not what a model will do.
"""
import json
import os
import subprocess
import threading
from pathlib import Path

SERVER = Path(os.environ.get("MONEYGUIDE_MCP", Path.home() / "moneyguide" / "mcp" / "dist" / "server.mjs"))
PROTOCOL = "2025-06-18"


class PlanningTools:
    def __init__(self):
        if not SERVER.exists():
            raise SystemExit(f"MCP server not built: {SERVER}. Run `npm run mcp:build` in ~/moneyguide.")
        self.proc = subprocess.Popen(["node", str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.lock = threading.Lock()
        self.next_id = 0
        init = self._request("initialize", {"protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": {"name": "plannerbench", "version": "1"}})
        self.server_info = init["serverInfo"]
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.tools = self._request("tools/list", {})["tools"]

    def _send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _request(self, method, params):
        # One request at a time: the engine answers in microseconds, so a lock costs nothing and keeps ids simple.
        with self.lock:
            self.next_id += 1
            self._send({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
            while True:
                line = self.proc.stdout.readline()
                if not line:
                    raise RuntimeError("MCP server exited")
                msg = json.loads(line)
                if msg.get("id") == self.next_id:
                    if "error" in msg:
                        raise RuntimeError(f"MCP {method}: {msg['error']}")
                    return msg["result"]

    def list(self):
        """Tool definitions in the Claude API's shape."""
        return [{"name": t["name"], "description": t["description"], "input_schema": t["inputSchema"]} for t in self.tools]

    def call(self, name, args):
        """(result text, is_error). A bad argument comes back as an error the model can read and fix, like any MCP client."""
        r = self._request("tools/call", {"name": name, "arguments": args})
        text = "".join(c.get("text", "") for c in r.get("content", []))
        return text, bool(r.get("isError"))

    def value(self, name, **args):
        text, err = self.call(name, args)
        if err:
            raise RuntimeError(f"{name}{args}: {text}")
        return json.loads(text)

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)


FILING = {"mfj": "married_filing_jointly", "single": "single"}


def oracle(t, case):
    """The answer a perfect tool user gives, or None for tasks the tools don't cover (compliance)."""
    i, task = case["inputs"], case["task"]

    def tax(filing, over65, ordinary, ltcg, ss, wages=0):
        return t.value("federal_income_tax", filing=FILING[filing], people_65_or_older=over65, wages=wages,
                       ordinary_income=ordinary, long_term_gains=ltcg, social_security_benefits=ss)

    def part_b(filing, magi):
        return t.value("medicare_part_b_premium", filing=FILING[filing], magi=magi)["part_b_monthly_per_person"]

    if task in ("federal_tax", "senior_phaseout"):
        return round(tax(i["filing"], i["over65"], i["ordinary"], i["ltcg"], i["ss"], i.get("wages", 0))["total_federal_tax"])
    if task == "taxable_ss":
        return round(t.value("taxable_social_security", filing=FILING[i["filing"]], social_security_benefits=i["ss"], other_income=i["other"])["taxable_social_security"])
    if task == "rmd":
        return round(t.value("required_minimum_distribution", birth_year=i["birthYear"], prior_year_end_balance=i["balance"])["rmd"])
    if task == "ss_claim":
        years, months = divmod(i["claimAgeMonths"], 12)
        return round(t.value("social_security_benefit", birth_year=i["birthYear"], pia=i["pia"], claim_age_years=years, claim_age_months=months)["monthly_benefit"])
    if task == "bracket_room":
        top = next(b["up_to_taxable_income"] for b in t.value("tax_tables", filing=FILING[i["filing"]])["ordinary_brackets"] if b["rate"] == i["rate"])
        return round(max(0, top - tax(i["filing"], 0, i["ordinary"], 0, 0)["taxable_income"]))
    if task == "irmaa":
        return part_b(i["filing"], i["magi"])
    if task == "tax_torpedo":
        before = tax(i["filing"], i["over65"], i["ordinary"], i["ltcg"], i["ss"])
        after = tax(i["filing"], i["over65"], i["ordinary"] + i["conversion"], i["ltcg"], i["ss"])
        return round(after["total_federal_tax"] - before["total_federal_tax"])
    if task == "widow_penalty":
        couple = tax("mfj", 2, i["ordinary"], i["ltcg"], i["ssA"] + i["ssB"])
        survivor = tax("single", 1, i["ordinary"], i["ltcg"], i["ssA"])
        return round(survivor["total_federal_tax"] - couple["total_federal_tax"])
    if task == "conversion_all_in":
        before = tax(i["filing"], i["over65"], i["ordinary"], i["ltcg"], i["ss"])
        after = tax(i["filing"], i["over65"], i["ordinary"] + i["conversion"], i["ltcg"], i["ss"])
        medicare = 12 * i["over65"] * (part_b(i["filing"], after["magi"]) - part_b(i["filing"], before["magi"]))
        return round(after["total_federal_tax"] - before["total_federal_tax"] + medicare)
    if task == "widow_all_in":
        couple = tax("mfj", 2, i["ordinary"], i["ltcg"], i["ssA"] + i["ssB"])
        survivor = tax("single", 1, i["ordinary"], i["ltcg"], i["ssA"])
        medicare = 12 * part_b("single", survivor["magi"]) - 24 * part_b("mfj", couple["magi"])
        return round(survivor["total_federal_tax"] - couple["total_federal_tax"] + medicare)
    return None


# ---- The Gauntlet ------------------------------------------------------------------------------------------------

def _years(plan):
    return {y["year"]: y for y in plan["years"]}


def gauntlet_oracle(t, case):
    """A perfect tool user on one Gauntlet question: every answer read off real run_scenario / solve_roth_conversion
    replies for the question's own facts. Returns (reply text, tool calls). The "tools are enough" check for the Gauntlet,
    and the stand-in model for `run_models.py --set gauntlet --fake --tools`."""
    import re

    calls = []

    def call(name, args):
        out, err = t.call(name, args)
        calls.append({"name": name, "input": args, "result": out, "is_error": err})
        if err:
            raise RuntimeError(f"{name}: {out}")
        return json.loads(out)

    if case["family"] == "trap":
        return "The facts given can't settle this.\nPICK: CANT", calls
    runs = {}
    for letter, sc in case["scenarios"].items():
        out = call("run_scenario", {"household": sc["household"], "plans": sc["plans"], "events": sc.get("events") or [], "assumptions": sc["assumptions"]})
        runs[letter] = out["plans"][0]
    yr = lambda l, y: _years(runs[l])[y]
    ids = {name: pid for pid, name in case["names"].items()}
    lines = []
    if case["how_much"]:
        sc = case["scenarios"]["A"]
        s = call("solve_roth_conversion", {"household": sc["household"], "events": sc.get("events") or [], "assumptions": sc["assumptions"],
                                           "from": case["how_much"]["from"], "max_years": case["how_much"]["maxYears"]})
        # Flat plans are labeled "$85,000 a year for 9 years (2026–2034)"; the amounts list shows what was actually converted.
        flat = [(m, x) for x in s["strategies"] if (m := re.match(r"\$([\d,]+) a year for (\d+) year", x["label"]))]
        m, best = max(flat, key=lambda f: f[1]["after_tax_wealth_gain_todays_dollars"])
        lines.append(f"PLAN: {m[1].replace(',', '')} x {m[2]}")
    else:
        wealth = {l: p["totals"]["after_tax_wealth_at_end_todays_dollars"] for l, p in runs.items()}
        top = max(wealth.values())
        near = [l for l in sorted(wealth, key=lambda l: -wealth[l]) if top - wealth[l] < 1000]
        lines.append(f"PICK: CLOSE {','.join(near)}" if len(near) > 1 else f"PICK: {near[0]}")
    for k, n in case["numbers"].items():
        a = n["ask"]
        if m := re.search(r"federal income tax would they owe for (\d{4}) under option (\w) than under option (\w)", a):
            y, b, base = int(m[1]), m[2], m[3]
            v = yr(b, y)["federal_tax"] - yr(base, y)["federal_tax"]
        elif m := re.search(r"Medicare premiums for (\d{4}) under option (\w) than under option (\w)", a):
            y, b, base = int(m[1]), m[2], m[3]
            prem = lambda l: sum(x["premium"] for x in yr(l, y)["medicare"].values())
            v = prem(b) - prem(base)
        elif "converted" in a and "federal income tax" in a:
            v = yr("P", 2026)["federal_tax"] - yr("A", 2026)["federal_tax"]
        elif "converted" in a and "Medicare" in a:
            prem = lambda l: sum(x["premium"] for x in yr(l, 2028)["medicare"].values())
            v = prem("P") - prem("A")
        elif m := re.search(r"Under option (\w), what is their total (\d{4}) senior deduction", a):
            v = yr(m[1], int(m[2]))["senior_deduction"]
        elif m := re.search(r"Under option (\w), how much of their (\d{4}) Social Security is taxable", a):
            v = yr(m[1], int(m[2]))["taxable_social_security"]
        elif m := re.search(r"Under option (\w), how much Social Security will (\w+) receive in total during (\d{4})", a):
            v = yr(m[1], int(m[3]))["social_security_by_person"][ids[m[2]]]
        elif m := re.search(r"What is (\w+)'s required minimum distribution for (\d{4})", a):
            v = yr(next(iter(runs)), int(m[2]))["rmd_by_account"][f"{ids[m[1]]}_ira"]
        elif m := re.search(r"required minimum distribution from (\w+)'s inherited IRA for (\d{4})", a):
            v = yr(next(iter(runs)), int(m[2]))["rmd_by_account"][f"{ids[m[1]]}_inherited"]
        else:
            raise ValueError(f"{case['id']} {k}: no tool reading for {a!r}")
        lines.append(f"{k}: {round(v)}")
    return "From the planning tools.\n" + "\n".join(lines), calls
