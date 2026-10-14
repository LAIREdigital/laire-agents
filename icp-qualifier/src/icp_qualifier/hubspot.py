"""HubSpot adapter for the LAIRE portal. Token from HUBSPOT_TOKEN (PAT or service key).

Every function takes an injectable `call` so tests never touch the network.
"""
import json
import os
import time
import urllib.request

BASE = "https://api.hubapi.com"
CONTACT_PROPS = [
    "email", "jobtitle", "company", "industry", "country", "numemployees",
    "hs_analytics_source", "createdate", "not_a_fit_", "quality_of_lead",
]
COMPANY_PROPS = ["industry", "numberofemployees", "country", "name"]


def _call(method, path, body=None):
    token = os.environ["HUBSPOT_TOKEN"]
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + token, "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search_recent(days, source=None, limit=100, call=_call, now=time.time):
    """Contacts created in the last `days` days, newest first. source like PAID_SOCIAL."""
    since = str(int((now() - days * 86400) * 1000))
    filters = [{"propertyName": "createdate", "operator": "GTE", "value": since}]
    if source:
        filters.append({"propertyName": "hs_analytics_source", "operator": "EQ", "value": source})
    out, after = [], None
    while len(out) < limit:
        body = {
            "filterGroups": [{"filters": filters}],
            "properties": CONTACT_PROPS,
            "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
            "limit": min(100, limit - len(out)),
        }
        if after:
            body["after"] = after
        page = call("POST", "/crm/v3/objects/contacts/search", body)
        out.extend({"id": r["id"], "properties": r.get("properties", {})} for r in page.get("results", []))
        after = page.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return out


def company_props(contact_ids, call=_call):
    """Map contact id to associated company properties (first company only)."""
    result = {}
    for i in range(0, len(contact_ids), 100):
        chunk = contact_ids[i:i + 100]
        assoc = call("POST", "/crm/v4/associations/contacts/companies/batch/read",
                     {"inputs": [{"id": c} for c in chunk]})
        pairs = {}
        for row in assoc.get("results", []):
            to = row.get("to") or []
            if to:
                pairs[str(row["from"]["id"])] = str(to[0]["toObjectId"])
        if not pairs:
            continue
        ids = sorted(set(pairs.values()))
        comps = call("POST", "/crm/v3/objects/companies/batch/read",
                     {"properties": COMPANY_PROPS, "inputs": [{"id": c} for c in ids]})
        by_id = {c["id"]: c.get("properties", {}) for c in comps.get("results", [])}
        for cid, coid in pairs.items():
            result[cid] = by_id.get(coid, {})
    return result


def to_lead(contact, company=None):
    """Scorer input. Contact fields win, associated company fills gaps."""
    p, c = contact["properties"], company or {}
    return {
        "email": p.get("email"),
        "jobtitle": p.get("jobtitle"),
        "company": p.get("company") or c.get("name"),
        "industry": p.get("industry") or c.get("industry"),
        "country": p.get("country") or c.get("country"),
        "numberofemployees": p.get("numemployees") or c.get("numberofemployees"),
    }


def build_props(result, mapping):
    """HubSpot properties to write for one verdict, from the approved mapping."""
    props = dict(mapping["verdicts"].get(result["verdict"], {}))
    if result["verdict"] == "bad_fit":
        table = mapping.get("why_disqualified_", {}).get("prefix_to_value", {})
        for reason in result["reasons"]:
            hit = next((v for k, v in table.items() if reason.startswith(k)), None)
            if hit:
                props["why_disqualified_"] = hit
                break
    return props


def already_set(contact, mapping):
    p = contact["properties"]
    return [k for k in mapping.get("skip_if_already_set", []) if p.get(k)]


def write_props(contact_id, props, call=_call):
    return call("PATCH", "/crm/v3/objects/contacts/" + str(contact_id), {"properties": props})
