---
name: cost-soma-application
description: Use inside the Cost SOMA team workflow to produce application method, writing format, choices needing confirmation, cautions, and draft purchase-purpose text.
---

# Cost SOMA Application

Generate the application bundle with:

```bash
python3 scripts/policy_tool.py form --question "$QUESTION"
python3 scripts/policy_tool.py docs --category "$CATEGORY"
python3 scripts/policy_tool.py form-packet --question "$QUESTION" --category "$CATEGORY" --stage "$STAGE" --payment-method "$PAYMENT_METHOD" --known-values-file known-values.json
```

Return 신청방법, 글쓰기 포맷, `writing_format_text` exactly as returned by the script when present, confirmation choices, draftable fields, 유의사항, and required documents.

Do not regroup board writing fields into `공통` and item-specific subsections. Preserve the support-item board format and field order from `writing_format_text`, including `구분`, `제목`, `상세구분`, `품목명`, `결제방식`, `세부사항`, `수량`, `금액`, `구매사유`, and `첨부파일` when present.

When actual DOCX/XLSX artifacts may be needed, also return the form packet summary: templates, source paths, missing fields, manual steps, and artifact instructions.

Ask for choices only where confirmation is genuinely needed. Do not write the final answer. Do not use web search.
