import argparse
import json
import os
import sys

from . import score_lead, slack_text
from .model import refine


def main(argv=None):
    p = argparse.ArgumentParser(prog="icp_qualifier")
    p.add_argument("--icp", required=True, help="client ICP json")
    p.add_argument("--lead", required=True, help="lead json file")
    p.add_argument("--write", action="store_true", help="write to HubSpot (needs HUBSPOT_TOKEN and --contact-id)")
    p.add_argument("--contact-id")
    a = p.parse_args(argv)

    icp = json.load(open(a.icp))
    lead = json.load(open(a.lead))
    result = score_lead(lead, icp)
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "system.md")
    result = refine(lead, icp, result, open(prompt_path).read())
    print(json.dumps(result, indent=2))
    print(slack_text(lead, result, icp.get("client", "")))

    if a.write:
        print("Write mode is off until the HubSpot property mapping is approved.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
