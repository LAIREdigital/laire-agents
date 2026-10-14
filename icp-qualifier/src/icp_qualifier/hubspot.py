"""HubSpot adapter. Read and write behind a token. Writes are off unless asked."""
import json
import os
import urllib.request

BASE = "https://api.hubapi.com"
PROPS = ["email", "jobtitle", "company", "industry", "country", "numberofemployees"]


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


def fetch_lead(contact_id):
    c = _call("GET", "/crm/v3/objects/contacts/%s?properties=%s" % (contact_id, ",".join(PROPS)))
    return c.get("properties", {})


def write_result(contact_id, props):
    """props is a dict of HubSpot property name to value, from the approved mapping."""
    return _call("PATCH", "/crm/v3/objects/contacts/" + str(contact_id), {"properties": props})
