---
name: cost-soma-evidence-viewer
description: Render Cost SOMA source evidence documents into a local HTML viewer. Use when the user asks to show, open, render, inspect, or view the original evidence, Markdown source, cited documents, or source lines behind a Cost SOMA answer.
---

# Cost SOMA Evidence Viewer

Generate a local HTML evidence viewer from the bundled Markdown documents.

## Workflow

1. Use the user's question as `$QUESTION`. If the user asks about the prior answer, reuse the original Cost SOMA question from context.
2. If a support category is already known, pass it as `$CATEGORY`. Otherwise omit `--category`.
3. Resolve the renderer path shown below relative to this skill directory.
4. Run the renderer:

```bash
python3 ../../scripts/render_evidence_view.py --question "$QUESTION" --category "$CATEGORY"
```

When this skill is copied into a target project during activation, the renderer command is rewritten to the absolute plugin script path.

## Reporting

After the command completes, report:

- generated `viewer_path`
- clickable `viewer_url` when available
- source filenames included in the viewer

Do not paste the full source document into chat. If generation fails, report the script output and the question/category used.
