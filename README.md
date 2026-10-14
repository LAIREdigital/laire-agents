# LAIRE agents

- `docs/agent-architecture.md`: Brainstorm Agent Architecture. Catalog, shared lifecycle, decisions.
- `_template/`: copy for every new agent.
- `icp-qualifier/`: Agent 1. Scores new leads against a client ICP, tells the owner why.

Lifecycle for every agent: plan usage, train on context and ICP, configure, test outputs, launch.

Public repo. Never commit client data, ICP docs, tokens, or lead records. Keep
per client context in the client Drive and pass it in at run time.

Tests: `cd icp-qualifier && python3 -m unittest discover -s tests`
