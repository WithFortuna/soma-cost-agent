---
name: cost-soma-evidence
description: Use inside the Cost SOMA team workflow to collect document-backed support-item candidates, supporting evidence, conflicting evidence, and source references.
---

# Cost SOMA Evidence

Classify the original question and search local evidence with:

```bash
python3 scripts/policy_tool.py classify --question "$QUESTION"
python3 scripts/policy_tool.py search --query "$QUESTION" --category "$CATEGORY"
```

Return candidate support items, supporting evidence, conflicting evidence, source filenames/lines, and ambiguity. Do not write the final answer. Do not use web search.
