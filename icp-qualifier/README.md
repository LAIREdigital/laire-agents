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

## Run on LAIRE HubSpot contacts

```
export HUBSPOT_TOKEN=...            # LAIRE private app token or service key
cd icp-qualifier
PYTHONPATH=src python3 -m icp_qualifier list-icps
PYTHONPATH=src python3 -m icp_qualifier run --icp-name acme --days 7 --source PAID_SOCIAL
```

- Pulls contacts created in the last N days (portal 533215). `--source` filters Original Source, e.g. `PAID_SOCIAL`.
- Fills missing industry, size, country from the associated company.
- HubSpot stores contact size as a range ("5-25"). A range that overlaps the ICP range counts as a fit.
- Report only by default. Prints verdict, score, reasons per contact.

## Saved ICPs

Saved ICPs are JSON files in a folder (`./icps`, or `$ICP_DIR`, or `--icp-dir`). `icps/` is gitignored.
The shared copy lives in the Drive folder "LAIRE ICP Qualifier - Saved ICPs". Download a file into `icps/` and use its name.
The site's Download file and Load from file buttons use the same format.

## Writing back to HubSpot

`run --write` is blocked until `hubspot_mapping.json` has `"approved": true`.
Proposed mapping (needs sign-off): good_fit sets `not_a_fit_` Yes and `quality_of_lead` High;
borderline sets Medium; bad_fit sets No and Low, plus `why_disqualified_` Industry or Company Size when the reason says so.
Never overwrites a contact where `not_a_fit_` or `quality_of_lead` is already set.
