from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_common() -> ModuleType:
    for filename in ("cse-harness-common.py", "harness_common.py"):
        path = Path(__file__).resolve().with_name(filename)
        if not path.exists():
            continue
        spec = importlib.util.spec_from_file_location("cse_harness_common", path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("missing Cost SOMA hook common module")


common = load_common()


def main() -> int:
    event = common.read_stdin_json()
    text = common.text_from_event(event)
    is_policy = common.looks_like_policy_question(text)
    common.write_audit(
        "cse-user-prompt-submit",
        {
            "is_policy_like": is_policy,
            "text_preview": text[:500],
        },
    )

    if is_policy:
        docs = common.document_root()
        docs_text = str(docs) if docs else "document/rules.json and document/*.md"
        tool_text = str(common.policy_tool_path())
        common.emit_user_prompt_context(
            "[Cost SOMA Policy Harness]\n"
            "This looks like a Cost SOMA activity-expense policy question. "
            "Always use team mode. Use the cost-soma-policy-orchestrator skill. "
            "Use only local documents "
            f"from {docs_text} through {tool_text}. "
            "Spawn custom subagents cse-policy-evidence and cse-policy-application in parallel, "
            "wait for both summaries, draft the answer, then spawn cse-policy-reviewer before "
            "the final answer. Keywords are routing hints only; final decisions require "
            "document evidence, supporting/conflicting evidence review, source filenames, "
            "item-specific 신청방법, 글쓰기 포맷 with choice-required fields, and 유의사항. "
            "For 글쓰기 포맷, use writing_format_text from policy_tool.py form/docs when present; "
            "preserve the board-entry field order and do not regroup it into 공통/item subsections. "
            "If the user asks for an actual DOCX/XLSX form, use policy_tool.py form-packet first, "
            "ask for missing_required_fields, then create only local files under outputs/cost-soma-forms "
            "with Documents/Spreadsheets; do not upload externally. "
            "Final answer sections must be 결론, 신청방법, 글쓰기 포맷, 유의사항, 근거."
        )
    else:
        common.emit_user_prompt_context()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
