from __future__ import annotations

import json
import importlib.util
import os
import re
import subprocess
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


def answer_from_event(event: dict) -> str:
    for key in ("last_assistant_message", "assistant_message", "output", "response", "message", "text"):
        item = event.get(key)
        if isinstance(item, str) and item.strip():
            return item
    return common.text_from_event(event)


def question_from_event(event: dict) -> str:
    for key in ("prompt", "user_prompt", "input", "question"):
        item = event.get(key)
        if isinstance(item, str) and item.strip():
            return item
    return ""


def validate_with_tool(question: str, answer: str) -> dict:
    command = [
        common.python_path(),
        str(common.policy_tool_path()),
        "validate",
        "--question",
        question,
        "--answer-file",
        "-",
    ]
    env = os.environ.copy()
    docs = common.document_root()
    if docs:
        env["COST_SOMA_DOCUMENT_ROOT"] = str(docs)
    try:
        proc = subprocess.run(
            command,
            input=answer,
            text=True,
            capture_output=True,
            cwd=str(common.repo_root()),
            env=env,
            timeout=12,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - hook safety boundary
        return {"ok": False, "error": str(exc), "findings": [f"policy_tool validate failed: {exc}"]}

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return {
            "ok": False,
            "returncode": proc.returncode,
            "error": detail[:1000],
            "findings": ["policy_tool validate returned a non-zero exit code."],
        }

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "error": f"invalid JSON from policy_tool validate: {exc}",
            "stdout_preview": proc.stdout[:1000],
            "findings": ["policy_tool validate returned invalid JSON."],
        }

    return payload


FORM_GENERATION_RE = re.compile(
    r"(양식\s*작성|신청서\s*작성|증빙문서\s*작성|제출용|파일\s*만들|문서\s*만들|docx|xlsx)",
    re.IGNORECASE,
)


FORM_HANDOFF_RE = re.compile(
    r"(form[_-]?packet|prepare_policy_form_packet|missing_required_fields|누락|입력 필요|"
    r"manual_steps|remaining_submission_requirements|수동|직접\s*첨부|서명|제출\s*전|"
    r"outputs/cost-soma-forms|\.docx|\.xlsx)",
    re.IGNORECASE,
)


def add_form_artifact_findings(question: str, answer: str, findings: list[str]) -> list[str]:
    if (
        common.looks_like_policy_question(" ".join([question or "", answer or ""]))
        and FORM_GENERATION_RE.search(question or "")
        and not FORM_HANDOFF_RE.search(answer or "")
    ):
        return [
            *findings,
            "Form-generation request missing form packet, generated artifact path, or missing-required-fields handoff.",
        ]
    return findings


def main() -> int:
    event = common.read_stdin_json()
    question = question_from_event(event)
    answer = answer_from_event(event)
    validation = validate_with_tool(question, answer)
    findings = add_form_artifact_findings(question, answer, list(validation.get("findings", [])))
    common.write_audit(
        "cse-stop-policy-review",
        {
            "question_preview": question[:500],
            "findings": findings,
            "validation": validation,
            "text_preview": answer[:1000],
        },
    )

    if findings:
        common.emit_stop_result(
            "[Cost SOMA Policy Harness Audit]\n"
            "Potential policy-answer issues detected: "
            + "; ".join(findings)
            + "\nUse policy_tool.py validate and revise if this was a Cost SOMA policy answer."
        )
    else:
        common.emit_stop_result()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
