---
name: cost-soma-answer-review
description: Use inside the Cost SOMA team workflow to review a draft answer for missing sections, missing evidence, unsafe certainty, and category-specific omissions.
---

# Cost SOMA Answer Review

Validate draft answers with:

```bash
python3 scripts/policy_tool.py validate --question "$QUESTION" --answer-file "$DRAFT_FILE"
```

Check for required sections, source-backed claims, unsafe certainty, and category-specific omissions.

For material purchase answers, verify the draft preserves the board writing format instead of regrouping into `공통`/item subsections, and includes `제목`, `상세구분`, VAT-included total amount, purchase-agency `0` amount rule, and `첨부파일`.

If the user requested actual form-file generation, require a form packet, generated artifact path, or missing-required-fields handoff.

Return findings and revision suggestions only. Do not write the final answer.
