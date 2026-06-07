Answer this Cost SOMA activity-expense policy question using the Cost Soma Policy Harness v2.

Workflow:

1. If `.codex/cost-soma-policy-harness.json` is missing in the current project, use `cost-soma-activate-project` first.
2. Use the `cost-soma-policy-orchestrator` skill.
3. Spawn `policy-evidence` and `policy-application` subagents in parallel.
4. Have both subagents use `scripts/policy_tool.py` through local scripts.
5. Draft the answer in Korean with `결론`, `신청방법`, `글쓰기 포맷`, `유의사항`, and `근거`.
6. Spawn `policy-reviewer` with the original question and draft answer.
7. Revise the final answer from reviewer findings.
8. If the user asked for an actual submit-ready form file, run `form-packet`, ask for any `missing_required_fields`, follow template `guidelines`, then use Documents for `.docx` or Spreadsheets for `.xlsx` generation and QA. Report any `remaining_submission_requirements` such as signatures, evidence images, receipt images, or ID/bank copies. Do not upload externally.

Script commands:

```bash
python3 scripts/policy_tool.py classify --question "$QUESTION"
python3 scripts/policy_tool.py form --question "$QUESTION"
python3 scripts/policy_tool.py form-packet --question "$QUESTION" --category "$CATEGORY" --stage "$STAGE" --payment-method "$PAYMENT_METHOD" --known-values-file known-values.json
python3 scripts/policy_tool.py validate-artifacts --form-packet-file form_packet.json --artifact outputs/cost-soma-forms/<timestamp>/<file>
python3 scripts/policy_tool.py validate --question "$QUESTION" --answer-file "$DRAFT_FILE"
```

Do not decide from keywords alone. If evidence is missing or conflicting, say `문서상 확인 불가` or `사무국 확인 필요`.
