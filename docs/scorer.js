// Browser port of icp-qualifier/src/icp_qualifier/scorer.py. Keep in sync.
(function (root) {
  var SENIORITY_DEFAULT = ["owner", "founder", "ceo", "vp", "director", "head", "chief", "manager"];
  function s(v) { return String(v == null ? "" : v).trim(); }
  function num(v) { var n = parseFloat(v); return isNaN(n) ? null : n; }
  function lc(a) { return (a || []).map(function (x) { return String(x).toLowerCase(); }); }

  // Accepts 150, "5-25", "1000+". A range fits when it overlaps the ICP range.
  function employeeRange(v) {
    var t = s(v).replace(/,/g, "");
    if (!t) return null;
    if (/\+$/.test(t) && num(t.slice(0, -1)) != null) return [num(t.slice(0, -1)), Infinity];
    if (t.indexOf("-") > 0) {
      var p = t.split("-"), x = num(p[0]), y = num(p[1]);
      return x != null && y != null ? [x, y] : null;
    }
    var n = num(t);
    return n == null ? null : [n, n];
  }

  function disqualifiers(lead, r) {
    var hits = [], ind = s(lead.industry).toLowerCase(), c = s(lead.country).toLowerCase();
    if (ind && lc(r.industries).indexOf(ind) >= 0) hits.push("Excluded industry: " + s(lead.industry));
    if (c && lc(r.countries).indexOf(c) >= 0) hits.push("Excluded country: " + s(lead.country));
    var email = s(lead.email).toLowerCase(), dom = email.indexOf("@") >= 0 ? email.split("@").pop() : "";
    if (dom && lc(r.free_email_domains).indexOf(dom) >= 0) hits.push("Free email domain: " + dom);
    var title = s(lead.jobtitle).toLowerCase(), kws = r.title_keywords || [];
    for (var i = 0; i < kws.length; i++) {
      if (title.indexOf(kws[i].toLowerCase()) >= 0) { hits.push("Title contains '" + kws[i] + "'"); break; }
    }
    return hits;
  }

  function criteria(lead, crit) {
    var score = 0, reasons = [], c;
    if ((c = crit.industry)) {
      var ind = s(lead.industry);
      if (!ind) reasons.push("Industry missing");
      else if (lc(c.good).indexOf(ind.toLowerCase()) >= 0) score += c.weight;
      else reasons.push("Industry off ICP: " + ind);
    }
    if ((c = crit.employees)) {
      var rng = employeeRange(lead.numberofemployees), lo = c.min == null ? 0 : c.min, hi = c.max == null ? Infinity : c.max;
      if (rng == null) reasons.push("Company size missing");
      else if (rng[0] <= hi && rng[1] >= lo) score += c.weight;
      else reasons.push("Company size " + s(lead.numberofemployees) + " outside " + lo + " to " + (c.max == null ? 0 : c.max));
    }
    if ((c = crit.seniority)) {
      var t = s(lead.jobtitle).toLowerCase(), good = lc(c.good || SENIORITY_DEFAULT);
      if (!t) reasons.push("Job title missing");
      else if (good.some(function (k) { return t.indexOf(k) >= 0; })) score += c.weight;
      else reasons.push("Title not decision level: " + s(lead.jobtitle));
    }
    if ((c = crit.country)) {
      var co = s(lead.country);
      if (!co) reasons.push("Country missing");
      else if (lc(c.good).indexOf(co.toLowerCase()) >= 0) score += c.weight;
      else reasons.push("Country off ICP: " + co);
    }
    var total = Object.keys(crit).reduce(function (a, k) { return a + (crit[k].weight || 0); }, 0) || 1;
    return { score: Math.round(100 * score / total), reasons: reasons };
  }

  function scoreLead(lead, icp) {
    var hits = disqualifiers(lead, icp.disqualifiers || {});
    if (hits.length) return { verdict: "bad_fit", score: 0, reasons: hits, source: "disqualifier" };
    var r = criteria(lead, icp.criteria || {}), t = icp.thresholds || { good: 70, borderline: 40 };
    var v = r.score >= t.good ? "good_fit" : r.score >= t.borderline ? "borderline" : "bad_fit";
    return { verdict: v, score: r.score, reasons: r.reasons, source: "rules" };
  }

  function slackText(lead, res, client) {
    var name = s(lead.company) || s(lead.email) || "Unknown lead";
    return "[" + (client || "ICP") + "] " + name + ": " + res.verdict + " (score " + res.score + ")\nWhy: " +
      (res.reasons.join("; ") || "Matches ICP criteria");
  }

  var api = { scoreLead: scoreLead, slackText: slackText };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.ICP = api;
})(typeof window !== "undefined" ? window : this);
