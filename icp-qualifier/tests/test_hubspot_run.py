import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from icp_qualifier import hubspot, __main__ as cli  # noqa: E402
from icp_qualifier import score_lead  # noqa: E402

with open(os.path.join(ROOT, "context", "icp.example.json")) as f:
    ICP = json.load(f)
with open(os.path.join(ROOT, "hubspot_mapping.json")) as f:
    MAPPING = json.load(f)


def fake_hubspot(log):
    contacts = [
        {"id": "1", "properties": {"email": "jane@acmefin.com", "jobtitle": "VP Marketing", "industry": "Financial Services", "country": "United States", "numemployees": "100-500"}},
        {"id": "2", "properties": {"email": "x@gmail.com", "jobtitle": "Student", "industry": "Education", "numemployees": "1-5"}},
        {"id": "3", "properties": {"email": "held@corp.com", "jobtitle": "Intern", "not_a_fit_": "Yes"}},
        {"id": "4", "properties": {"email": "co@buildco.com", "jobtitle": "Owner", "numemployees": ""}},
    ]

    def call(method, path, body=None):
        log.append((method, path, body))
        if path.endswith("/contacts/search"):
            return {"results": contacts}
        if "associations" in path:
            return {"results": [{"from": {"id": "4"}, "to": [{"toObjectId": 99}]}]}
        if "companies/batch/read" in path:
            return {"results": [{"id": "99", "properties": {"industry": "Construction", "numberofemployees": "50", "country": "United States", "name": "BuildCo"}}]}
        if method == "PATCH":
            return {}
        raise AssertionError(path)
    return call


class Pieces(unittest.TestCase):
    def test_range_overlap_counts_as_fit(self):
        lead = {"industry": "Software", "jobtitle": "CEO", "country": "Canada", "numberofemployees": "100-500", "email": "a@b.com"}
        self.assertEqual(score_lead(lead, ICP)["verdict"], "good_fit")

    def test_small_range_misses(self):
        lead = {"industry": "Software", "jobtitle": "CEO", "country": "Canada", "numberofemployees": "1-5", "email": "a@b.com"}
        self.assertIn("Company size 1-5 outside 20 to 1000", score_lead(lead, ICP)["reasons"])

    def test_open_ended_range(self):
        self.assertEqual(hubspot.to_lead({"properties": {"numemployees": "1000+"}})["numberofemployees"], "1000+")
        from icp_qualifier.scorer import employee_range
        self.assertEqual(employee_range("1000+"), (1000.0, float("inf")))

    def test_company_fills_gaps_contact_wins(self):
        lead = hubspot.to_lead({"properties": {"industry": "A"}}, {"industry": "B", "country": "US"})
        self.assertEqual((lead["industry"], lead["country"]), ("A", "US"))

    def test_build_props_good_and_bad(self):
        self.assertEqual(hubspot.build_props({"verdict": "good_fit", "reasons": []}, MAPPING),
                         {"not_a_fit_": "Yes", "quality_of_lead": "High"})
        bad = hubspot.build_props({"verdict": "bad_fit", "reasons": ["Free email domain: gmail.com", "Excluded industry: Education"]}, MAPPING)
        self.assertEqual(bad["why_disqualified_"], "Industry")
        self.assertEqual(bad["not_a_fit_"], "No")

    def test_mapping_ships_unapproved(self):
        self.assertFalse(MAPPING["approved"])


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        with open(os.path.join(self.tmp, "acme.json"), "w") as f:
            json.dump(ICP, f)
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def args(self, *extra):
        return ["run", "--icp-name", "acme", "--icp-dir", self.tmp, "--days", "7"] + list(extra)

    def test_report_only_writes_nothing(self):
        log = []
        self.assertEqual(cli.main(self.args(), call=fake_hubspot(log)), 0)
        self.assertFalse([l for l in log if l[0] == "PATCH"])
        search = log[0][2]
        self.assertEqual(search["filterGroups"][0]["filters"][0]["propertyName"], "createdate")

    def test_source_filter(self):
        log = []
        cli.main(self.args("--source", "PAID_SOCIAL"), call=fake_hubspot(log))
        names = [f["propertyName"] for f in log[0][2]["filterGroups"][0]["filters"]]
        self.assertIn("hs_analytics_source", names)

    def test_write_blocked_until_approved(self):
        log = []
        self.assertEqual(cli.main(self.args("--write"), call=fake_hubspot(log)), 2)
        self.assertEqual(log, [])

    def test_write_skips_human_set_and_uses_company(self):
        log = []
        orig = cli.MAPPING
        approved = os.path.join(self.tmp, "m.json")
        with open(approved, "w") as f:
            json.dump(dict(MAPPING, approved=True), f)
        cli.MAPPING = approved
        try:
            self.assertEqual(cli.main(self.args("--write"), call=fake_hubspot(log)), 0)
        finally:
            cli.MAPPING = orig
        patches = {l[1].rsplit("/", 1)[1]: l[2]["properties"] for l in log if l[0] == "PATCH"}
        self.assertNotIn("3", patches)  # human already set not_a_fit_
        self.assertEqual(patches["1"]["quality_of_lead"], "High")
        self.assertEqual(patches["2"]["not_a_fit_"], "No")
        self.assertIn("4", patches)  # Construction from associated company

    def test_missing_icp_lists_saved(self):
        with self.assertRaises(SystemExit) as e:
            cli.load_icp(self.tmp, "nope")
        self.assertIn("acme", str(e.exception))

    def test_list_icps(self):
        self.assertEqual(cli.list_icps(self.tmp), ["acme"])


if __name__ == "__main__":
    unittest.main()
