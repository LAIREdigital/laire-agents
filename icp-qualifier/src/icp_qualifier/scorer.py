"""Rule based ICP scoring. Pure functions, no network."""

SENIORITY_DEFAULT = ["owner", "founder", "ceo", "vp", "director", "head", "chief", "manager"]


def _s(value):
    return str(value or "").strip()


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def employee_range(value):
    """Parse 150, '150', '5-25', '1000+' into (low, high). None if unknown.

    HubSpot contacts store size as a range string, so a range counts as a fit
    when it overlaps the ICP range.
    """
    t = _s(value).replace(",", "")
    if not t:
        return None
    if t.endswith("+") and _num(t[:-1]) is not None:
        return (_num(t[:-1]), float("inf"))
    if "-" in t:
        a, _, b = t.partition("-")
        if _num(a) is not None and _num(b) is not None:
            return (_num(a), _num(b))
        return None
    n = _num(t)
    return None if n is None else (n, n)


def _disqualifiers(lead, rules):
    hits = []
    industry = _s(lead.get("industry")).lower()
    if industry and industry in [i.lower() for i in rules.get("industries", [])]:
        hits.append("Excluded industry: " + _s(lead.get("industry")))
    country = _s(lead.get("country")).lower()
    if country and country in [c.lower() for c in rules.get("countries", [])]:
        hits.append("Excluded country: " + _s(lead.get("country")))
    email = _s(lead.get("email")).lower()
    domain = email.split("@")[-1] if "@" in email else ""
    if domain and domain in [d.lower() for d in rules.get("free_email_domains", [])]:
        hits.append("Free email domain: " + domain)
    title = _s(lead.get("jobtitle")).lower()
    for kw in rules.get("title_keywords", []):
        if kw.lower() in title:
            hits.append("Title contains '" + kw + "'")
            break
    return hits


def _criteria(lead, crit):
    score, reasons = 0.0, []

    c = crit.get("industry")
    if c:
        industry = _s(lead.get("industry"))
        if not industry:
            reasons.append("Industry missing")
        elif industry.lower() in [i.lower() for i in c.get("good", [])]:
            score += c["weight"]
        else:
            reasons.append("Industry off ICP: " + industry)

    c = crit.get("employees")
    if c:
        rng = employee_range(lead.get("numberofemployees"))
        lo, hi = c.get("min", 0), c.get("max")
        hi = float("inf") if hi is None else hi
        if rng is None:
            reasons.append("Company size missing")
        elif rng[0] <= hi and rng[1] >= lo:
            score += c["weight"]
        else:
            reasons.append("Company size %s outside %d to %d" % (_s(lead.get("numberofemployees")), lo, c.get("max") or 0))

    c = crit.get("seniority")
    if c:
        title = _s(lead.get("jobtitle")).lower()
        if not title:
            reasons.append("Job title missing")
        elif any(k in title for k in c.get("good", SENIORITY_DEFAULT)):
            score += c["weight"]
        else:
            reasons.append("Title not decision level: " + _s(lead.get("jobtitle")))

    c = crit.get("country")
    if c:
        country = _s(lead.get("country"))
        if not country:
            reasons.append("Country missing")
        elif country.lower() in [g.lower() for g in c.get("good", [])]:
            score += c["weight"]
        else:
            reasons.append("Country off ICP: " + country)

    total = sum(v.get("weight", 0) for v in crit.values()) or 1
    return round(100 * score / total), reasons


def score_lead(lead, icp):
    """Return {verdict, score, reasons, source}. Gray band is flagged for the model."""
    hits = _disqualifiers(lead, icp.get("disqualifiers", {}))
    if hits:
        return {"verdict": "bad_fit", "score": 0, "reasons": hits, "source": "disqualifier"}
    score, reasons = _criteria(lead, icp.get("criteria", {}))
    t = icp.get("thresholds", {"good": 70, "borderline": 40})
    if score >= t["good"]:
        verdict = "good_fit"
    elif score >= t["borderline"]:
        verdict = "borderline"
    else:
        verdict = "bad_fit"
    return {"verdict": verdict, "score": score, "reasons": reasons, "source": "rules"}


def slack_text(lead, result, client=""):
    name = _s(lead.get("company")) or _s(lead.get("email")) or "Unknown lead"
    head = "[%s] %s: %s (score %s)" % (client or "ICP", name, result["verdict"], result["score"])
    return head + "\nWhy: " + ("; ".join(result["reasons"]) or "Matches ICP criteria")
