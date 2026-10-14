# HubSpot Agent Builder: ICP Qualifier

HubSpot agents cannot be created through the API or the connector I have. Build this
in the HubSpot UI (Agent Hub, Agent Builder). Everything below is paste ready.
Native ICP Qualifier agent is in beta, so check what it already does before building.

## Name
ICP Qualifier

## Goal
Judge whether a new contact fits the client ICP. Explain the single biggest reason.
Tell the contact owner. Never change lifecycle stage, owner, or delete anything.

## Trigger
Workflow: contact is created with Original Source in (Paid Social, Paid Search) OR
form submission from a paid campaign. Run on each new contact. If volume is high,
batch hourly to control credits.

## Context (paste the client ICP in the Knowledge field)
- Excluded industries, countries, free email domains, student or intern titles: automatic bad fit.
- Good industries, size range, decision level titles, target countries.
- Thresholds: good fit at 70 or more, borderline 40 to 69, bad fit under 40.
- Source: client ICP doc in Drive. Do not paste client data into the public repo.

## Instructions (paste)
You judge whether one HubSpot contact fits the ICP in your knowledge.
Use only the contact and associated company fields. If a field is empty, say it is missing.
1. Any automatic disqualifier means bad_fit.
2. Otherwise weigh industry (35), company size (25), job title seniority (25), country (15). Score 0 to 100.
3. Return verdict good_fit, borderline, or bad_fit, the score, and a reason of two sentences max. Biggest factor first.
4. Never infer anything from a person's name. Never invent company facts.

## Tools and actions
- Read contact and associated company properties.
- Update contact: `not_a_fit_` and `quality_of_lead` (confirm option values in portal first), plus an ICP fit reason property.
- Send Slack message to the contact owner or client channel with verdict and reason (bad_fit and borderline only).

## Test before launch
Run `icp-qualifier/tests/fixtures` style leads. Agreement with human verdict target: 85 percent on 50 labeled leads.

## Launch
Dry run on the LAIRE live portal with actions set to notify only. Then enable property updates. Then one client.
