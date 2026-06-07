---
name: cost-soma-deactivate-project
description: Deactivate or uninstall the Cost SOMA Policy Harness from the current Codex project. Use when the user asks to remove, disable, uninstall, deactivate, or roll back Cost SOMA harness project integration.
---

# Cost SOMA Deactivate Project

Deactivate the harness by running the bundled uninstaller against the target Codex project.

## Workflow

1. Use the current working directory as the target project unless the user gives a different path.
2. Resolve the uninstaller path shown below relative to this skill directory.
3. Run the uninstaller against the target:

```bash
python3 ../../install/deactivate.py --target "$TARGET"
```

When this skill is copied into a target project during activation, the uninstaller command is rewritten to the absolute plugin uninstaller path. The uninstaller removes Cost SOMA hook entries, copied hook scripts, custom agent files, repo-scoped Cost SOMA skills, and `.codex/cost-soma-policy-harness.json`. It backs up an existing `.codex/hooks.json` before editing and leaves unrelated project hooks alone.

## Reporting

After the command completes, report:

- target project path
- whether a hooks backup was created
- that unrelated hooks and project files were left intact

If deactivation fails, report the command output and avoid deleting files manually unless the target path is clearly wrong and the user confirms the intended project.
