---
name: cost-soma-activate-project
description: Activate or update the Cost SOMA Policy Harness in the current Codex project. Use when the user asks to enable, install, set up, activate, update, or one-click configure the Cost SOMA harness for a project.
---

# Cost SOMA Activate Project

Activate the harness by running the bundled installer against the target Codex project.

## Workflow

1. Use the current working directory as the target project unless the user gives a different path.
2. Ask the user which Cost SOMA custom-agent model to use before running the installer. Present these choices:
   - `gpt-5.5` (Recommended): strongest for evidence-heavy policy reasoning and review.
   - `gpt-5.4-mini`: faster and lower cost for lighter policy checks.
   - Custom model id: use only when the user explicitly gives a model/provider id.
3. Resolve the installer path shown below relative to this skill directory.
4. Run the installer against the target with the chosen model:

```bash
python3 ../../install/activate.py --target "$TARGET" --model "$MODEL"
```

When this skill is copied into a target project during activation, the installer command is rewritten to the absolute plugin installer path. The installer writes `.codex/hooks.json`, `.codex/hooks/cse-*.py`, `.codex/agents/cse-*.toml`, `.agents/skills/cost-soma-*`, and `.codex/cse-policy-harness.json`. It pins the selected model in the Cost SOMA custom agent files and records it in the state file. It backs up an existing `.codex/hooks.json` before merging Cost SOMA hooks, removes legacy Cost SOMA runtime files, and runs smoke checks by default.

## Reporting

After the command completes, report:

- target project path
- state file path
- configured model
- whether a hooks backup was created
- smoke result

If activation fails, report the command output and do not hand-edit project hook or agent files unless the failure clearly identifies a small local path issue.
