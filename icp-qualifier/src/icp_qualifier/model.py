"""Optional model pass for the borderline band. Stdlib HTTP, injectable for tests."""
import json
import os
import urllib.request

MODEL = "claude-sonnet-5-5"


def _post(payload, key):
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def refine(lead, icp, result, system_prompt, post=_post):
    """Return result with model verdict and reason, or unchanged if no key or bad output."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or result["verdict"] != "borderline":
        return result
    body = {"icp": icp, "lead": lead, "rule_result": result}
    resp = post(
        {"model": MODEL, "max_tokens": 300, "system": system_prompt,
         "messages": [{"role": "user", "content": json.dumps(body)}]},
        key,
    )
    try:
        out = json.loads(resp["content"][0]["text"])
        if out["verdict"] in ("good_fit", "borderline", "bad_fit"):
            return dict(result, verdict=out["verdict"], reasons=[out["reason"]] + result["reasons"], source="model")
    except (KeyError, IndexError, ValueError, TypeError):
        pass
    return result
