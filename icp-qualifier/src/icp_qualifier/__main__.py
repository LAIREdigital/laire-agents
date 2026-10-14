import argparse
import json
import os
import sys

from . import hubspot, score_lead, slack_text
from .model import refine

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
MAPPING = os.path.join(ROOT, "hubspot_mapping.json")


def _prompt():
    return open(os.path.join(ROOT, "prompts", "system.md")).read()


def icp_dir(arg=None):
    return arg or os.environ.get("ICP_DIR") or os.path.join(os.getcwd(), "icps")


def list_icps(d):
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def load_icp(d, name):
    path = os.path.join(d, name if name.endswith(".json") else name + ".json")
    if not os.path.isfile(path):
        raise SystemExit("No saved ICP '%s' in %s. Saved: %s" % (name, d, ", ".join(list_icps(d)) or "none"))
    with open(path) as f:
        return json.load(f)


def cmd_score(a):
    with open(a.icp) as f:
        icp = json.load(f)
    with open(a.lead) as f:
        lead = json.load(f)
    result = refine(lead, icp, score_lead(lead, icp), _prompt())
    print(json.dumps(result, indent=2))
    print(slack_text(lead, result, icp.get("client", "")))
    return 0


def cmd_run(a, call=hubspot._call):
    icp = load_icp(icp_dir(a.icp_dir), a.icp_name)
    with open(MAPPING) as f:
        mapping = json.load(f)
    if a.write and not mapping.get("approved"):
        print("Write blocked: hubspot_mapping.json is not approved.", file=sys.stderr)
        return 2
    contacts = hubspot.search_recent(a.days, a.source, a.limit, call=call)
    companies = hubspot.company_props([c["id"] for c in contacts], call=call)
    counts = {"good_fit": 0, "borderline": 0, "bad_fit": 0}
    written = skipped = 0
    for c in contacts:
        lead = hubspot.to_lead(c, companies.get(c["id"]))
        result = refine(lead, icp, score_lead(lead, icp), _prompt())
        counts[result["verdict"]] += 1
        note = ""
        if a.write:
            held = hubspot.already_set(c, mapping)
            props = hubspot.build_props(result, mapping)
            if held:
                skipped += 1
                note = "  [skipped, already set: %s]" % ", ".join(held)
            elif props:
                hubspot.write_props(c["id"], props, call=call)
                written += 1
                note = "  [wrote %s]" % json.dumps(props)
        print("%s | %s | %s | score %s | %s%s" % (
            c["id"], lead.get("email") or "no email", result["verdict"], result["score"],
            "; ".join(result["reasons"]) or "matches ICP", note))
    print("\nChecked %d contacts from the last %d days. good %d, maybe %d, bad %d.%s" % (
        len(contacts), a.days, counts["good_fit"], counts["borderline"], counts["bad_fit"],
        " Wrote %d, skipped %d." % (written, skipped) if a.write else " Report only, nothing written."))
    return 0


def main(argv=None, call=hubspot._call):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "run":
        p = argparse.ArgumentParser(prog="icp_qualifier run")
        p.add_argument("--icp-name", required=True, help="saved ICP name, file in the ICP folder")
        p.add_argument("--icp-dir", help="folder of saved ICP json files (default ./icps or $ICP_DIR)")
        p.add_argument("--days", type=int, default=7, help="contacts created in the last N days")
        p.add_argument("--source", help="HubSpot Original Source, e.g. PAID_SOCIAL")
        p.add_argument("--limit", type=int, default=100)
        p.add_argument("--write", action="store_true", help="write verdicts to HubSpot (needs approved mapping)")
        return cmd_run(p.parse_args(argv[1:]), call=call)
    if argv and argv[0] == "list-icps":
        p = argparse.ArgumentParser(prog="icp_qualifier list-icps")
        p.add_argument("--icp-dir")
        names = list_icps(icp_dir(p.parse_args(argv[1:]).icp_dir))
        print("\n".join(names) or "No saved ICPs.")
        return 0
    p = argparse.ArgumentParser(prog="icp_qualifier")
    p.add_argument("--icp", required=True, help="client ICP json")
    p.add_argument("--lead", required=True, help="lead json file")
    p.add_argument("--write", action="store_true")
    a = p.parse_args(argv)
    if a.write:
        print("Use the run command to write to HubSpot.", file=sys.stderr)
        return 2
    return cmd_score(a)


if __name__ == "__main__":
    sys.exit(main())
