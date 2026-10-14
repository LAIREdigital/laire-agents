# Agent 1: ICP Qualifier

Catch bad-fit leads the moment they hit the CRM, say why, tell the account owner,
so paid targeting gets fixed in days, not at month end.

Ask source: Chris Goodman, #ai-chatroom 2026-09-03. Accelo task 12396.

## Run

```
python3 -m icp_qualifier --icp context/icp.example.json --lead tests/fixtures/bad_fit.json
```

Needs `src` on the path: `cd agents/icp-qualifier && PYTHONPATH=src python3 -m icp_qualifier ...`

Dry run by default. Prints verdict, score, reasons, and the Slack text.
`--write` pushes to HubSpot and needs `HUBSPOT_TOKEN`. Leave it off until the
property mapping in `context/icp.example.json` is approved.

## How it scores

1. Hard disqualifiers (excluded industry, country, free email, student titles). Any hit is `bad_fit`.
2. Weighted criteria (industry, size, title seniority, geography). Score 0 to 100.
3. Gray band (default 40 to 69): optional model call with `prompts/system.md` for a reason. Off without `ANTHROPIC_API_KEY`.
4. Verdict: `good_fit`, `borderline`, `bad_fit`.

## HubSpot mapping (LAIRE live portal 533215, read only so far)

Existing properties found, reuse before creating: company `hs_ideal_customer_profile`,
`tal_tier`, `hs_is_target_account`; contact `not_a_fit_`, `quality_of_lead`.
Option values for `not_a_fit_` and `quality_of_lead` still need checking before `--write`.

## Per client setup

Copy `context/icp.example.json`, fill from the client ICP doc, run the evals in `tests/`.
