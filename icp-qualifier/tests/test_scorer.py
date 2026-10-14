import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ICP = os.path.join(ROOT, "context", "icp.example.json")
sys.path.insert(0, os.path.join(ROOT, "src"))

from icp_qualifier import score_lead, slack_text  # noqa: E402
from icp_qualifier.model import refine  # noqa: E402


def load(name):
    return json.load(open(os.path.join(HERE, "fixtures", name)))


ICP_CFG = json.load(open(ICP))


class Scorer(unittest.TestCase):
    def test_good(self):
        r = score_lead(load("good_fit.json"), ICP_CFG)
        self.assertEqual(r["verdict"], "good_fit")
        self.assertEqual(r["score"], 100)

    def test_disqualified(self):
        r = score_lead(load("bad_fit.json"), ICP_CFG)
        self.assertEqual(r["verdict"], "bad_fit")
        self.assertEqual(r["source"], "disqualifier")
        self.assertGreaterEqual(len(r["reasons"]), 3)

    def test_borderline_has_reason(self):
        r = score_lead(load("borderline.json"), ICP_CFG)
        self.assertEqual(r["verdict"], "borderline")
        self.assertIn("Title not decision level: Estimator", r["reasons"])

    def test_missing_fields_named(self):
        r = score_lead({"email": "x@corp.com"}, ICP_CFG)
        self.assertIn("Industry missing", r["reasons"])

    def test_slack_text(self):
        lead = load("bad_fit.json")
        txt = slack_text(lead, score_lead(lead, ICP_CFG), "EXAMPLE")
        self.assertTrue(txt.startswith("[EXAMPLE]"))
        self.assertIn("Why:", txt)


class Model(unittest.TestCase):
    def setUp(self):
        os.environ["ANTHROPIC_API_KEY"] = "test"

    def tearDown(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_refine_applies_verdict(self):
        base = score_lead(load("borderline.json"), ICP_CFG)
        fake = lambda payload, key: {"content": [{"text": '{"verdict": "good_fit", "reason": "Estimators buy."}'}]}
        out = refine({}, ICP_CFG, base, "sys", post=fake)
        self.assertEqual(out["verdict"], "good_fit")
        self.assertEqual(out["source"], "model")

    def test_refine_bad_output_keeps_rules(self):
        base = score_lead(load("borderline.json"), ICP_CFG)
        fake = lambda payload, key: {"content": [{"text": "not json"}]}
        self.assertEqual(refine({}, ICP_CFG, base, "sys", post=fake), base)

    def test_refine_skips_non_borderline(self):
        base = score_lead(load("good_fit.json"), ICP_CFG)
        boom = lambda *a, **k: 1 / 0
        self.assertEqual(refine({}, ICP_CFG, base, "sys", post=boom), base)


class Cli(unittest.TestCase):
    def test_cli_runs_as_subprocess(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
        env.pop("ANTHROPIC_API_KEY", None)
        out = subprocess.run(
            [sys.executable, "-m", "icp_qualifier", "--icp", ICP, "--lead", os.path.join(HERE, "fixtures", "bad_fit.json")],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("bad_fit", out.stdout)

    def test_write_flag_blocked(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
        out = subprocess.run(
            [sys.executable, "-m", "icp_qualifier", "--icp", ICP, "--lead", os.path.join(HERE, "fixtures", "good_fit.json"), "--write"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(out.returncode, 2)


if __name__ == "__main__":
    unittest.main()
