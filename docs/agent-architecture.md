# Brainstorm Agent Architecture

Status: draft for review. Sources: #ai-chatroom 2026-09-03 (Chris), #hs-ops
2026-10-09 (Sylvie, Lori, Sam), HubSpot Agent Hub show and tell 2026-08-21.
Accelo tasks 12395 (general) and 12396 (ICP qualifier build) not readable from
here. Check them for anything missing.

## Agent catalog

| # | Agent | Trigger | Human in loop | Needs HubSpot |
|---|-------|---------|---------------|---------------|
| 1 | ICP Qualifier | New lead or batch hits client CRM | Account owner reads reason, paid media acts on it | No. HubSpot first, CRM adapter later |
| 2 | Account Executive: Prep | Routine, X days before client call | AM reads brief | No |
| 2 | Account Executive: Debrief | Transcript lands | AM adds color before summary | No |

Agents, not tools: they fire on a trigger and act without being asked.

## Shared layers

1. Context: client ICP, personas, offers, exclusions. One markdown file per client. Source of truth is the client Drive Content Brief and ICP doc.
2. Trigger: webhook, workflow, or scheduled routine. Batch when volume or token cost demands it.
3. Reasoner: Claude with a fixed rubric plus free-text reasons. Deterministic checks first, model only for the gray band.
4. Adapter: CRM read and write. HubSpot first. Interface is two functions, `fetch_leads` and `write_result`.
5. Notify: Slack message to account owner with the reason. Never silent.
6. Feedback: owner marks verdict right or wrong. Feeds eval set and ICP doc edits.

## Lifecycle (use for every agent, every client)

1. Plan usage: what decision does it change, who acts, what is the cost ceiling.
2. Train on context: ICP doc, past good and bad leads, exclusion list.
3. Configure: rubric weights, thresholds, property mapping, Slack target.
4. Test outputs: run `evals/` cases, compare to human verdicts, target agreement before launch.
5. Launch: dry run, then write mode on one client, then roll out.

## Decisions made (small, reversible)

- Reuse existing LAIRE portal properties before creating any: `hs_ideal_customer_profile`, `tal_tier`, `not_a_fit_`, `quality_of_lead`.
- Dry run is default. Nothing writes to HubSpot without `--write`.
- Stdlib Python only. No framework until a second agent needs one.

## Open questions

- HubSpot native ICP Qualifier agent (beta) vs this build: compare on same 50 leads.
- Credit burn of native agent vs Claude API cost per lead.
- Where non-HubSpot clients push leads (Sheet, webhook, CSV).
- Which Slack channel the alerts post to per client.
