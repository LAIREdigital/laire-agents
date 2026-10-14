# LAIRE agents

## Use it

1. Open https://lairedigital.github.io/laire-agents/
2. Fill in the client profile and the lead, press Check lead.
3. Copy the message to Slack.

To run it automatically in HubSpot, use `docs/hubspot/icp-qualifier-agent.md`.

## What is here

- `docs/index.html`: the site. `docs/scorer.js` is the scoring logic.
- `docs/agent-architecture.md`: Brainstorm Agent Architecture. Catalog, shared lifecycle, decisions.
- `_template/`: copy for every new agent.
- `icp-qualifier/`: Agent 1. Scores new leads against a client ICP, tells the owner why.

Lifecycle for every agent: plan usage, train on context and ICP, configure, test outputs, launch.

Public repo. Never commit client data, ICP docs, tokens, or lead records. Keep
per client context in the client Drive and pass it in at run time.

Tests: `cd icp-qualifier && python3 -m unittest discover -s tests`
