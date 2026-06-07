---
name: cost-soma-activate-project
description: Activate or update the Cost SOMA Policy Harness in the current Codex project. Use when the user asks to enable, install, set up, activate, update, or one-click configure the Cost SOMA harness for a project.
---

# Cost SOMA Activate Project

Activate the harness by running the bundled installer against the target Codex project.

## Workflow

1. Use the current working directory as the target project unless the user gives a different path.
2. Resolve the installer path shown below relative to this skill directory.
3. Run the installer against the target:

```bash
python3 ../../install/activate.py --target "$TARGET"
```

When this skill is copied into a target project during activation, the installer command is rewritten to the absolute plugin installer path. The installer writes `.codex/hooks.json`, `.codex/hooks/*.py`, `.codex/agents/*.toml`, `.agents/skills/cost-soma-*`, and `.codex/cost-soma-policy-harness.json`. It backs up an existing `.codex/hooks.json` before merging Cost SOMA hooks and runs smoke checks by default.

## Reporting

After the command completes, report:

- target project path
- state file path
- whether a hooks backup was created
- smoke result

If activation fails, report the command output and do not hand-edit project hook or agent files unless the failure clearly identifies a small local path issue.
