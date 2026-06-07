---
name: cost-soma-policy-orchestrator
description: Use for any Cost SOMA/SW Maestro activity-expense policy question. Coordinates always-team-mode subagents, script-backed evidence/form checks, and the final Korean answer shape.
---

# Cost SOMA Policy Orchestrator

Use this skill for Cost SOMA policy questions about supportability, applications, writing formats, or cautions.

## Runtime Rule

- macOS/local Python runtime.
- Use only local scripts and documents.
- Use local documents only: `document/rules.json` and `document/*.md`.
- Use JSON-only script commands from the repo root:

```bash
python3 scripts/policy_tool.py classify --question "$QUESTION"
python3 scripts/policy_tool.py form --question "$QUESTION"
python3 scripts/policy_tool.py search --query "$QUERY" --category "$CATEGORY"
python3 scripts/policy_tool.py form-packet --question "$QUESTION" --category "$CATEGORY" --stage "$STAGE" --known-values-file known-values.json
```

## Always Team Mode

1. Spawn `policy-evidence` and `policy-application` in parallel.
2. Wait for both summaries.
3. Draft the answer.
4. Spawn `policy-reviewer`.
5. Revise and finalize.
6. If the user asked for an actual DOCX/XLSX form, run the form artifact flow after policy review.

If custom subagents are unavailable, run the same script-backed workflow directly and continue.

## Actual Form Artifact Flow

For real submit-ready forms:

- Run `policy_tool.py form-packet` with the confirmed category, stage, payment method, and known values.
- Ask only for `missing_required_fields` before final generation. Create a partial placeholder draft only if the user explicitly asks.
- Follow the returned template `guidelines`; any unmet or unverifiable guideline must be reported as a remaining submission requirement.
- Use Documents for `.docx` and Spreadsheets for `.xlsx`; save generated files under `outputs/cost-soma-forms/<timestamp>/`.
- After artifact validation, report generated-file QA separately from `submission_ready`.
- Run `policy_tool.py validate-artifacts` after generating files.
- Do not upload externally or infer signatures, resident registration numbers, ID/bank copies, or real evidence images.

## Final Answer Shape

Always answer in Korean with `결론`, `신청방법`, `글쓰기 포맷`, `유의사항`, and `근거`, in that order.

In `글쓰기 포맷`, use `writing_format_text` from `policy_tool.py form/docs` when present. Keep the board-entry field order and wording; do not regroup the section into `공통` and item-by-item subsections.

Base decisions on document evidence, not keyword-only assumptions.
