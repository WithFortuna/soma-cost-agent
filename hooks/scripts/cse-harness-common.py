from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


POLICY_HINT_RE = re.compile(
    r"(?i)(soma|sw\s*maestro|활동비|지원|증빙|양식|서식|신청서|지급요청서|사무국|멘토|구매|결제|정산|aws|클라우드|"
    r"디바이스마트|허브|도킹|독|외주|디자인|전문가|마케팅|기자재|재료|ai|sw|서비스)"
)
STATE_NAMES = ["cse-policy-harness.json", "cost-soma-policy-harness.json"]


def state_path() -> Path | None:
    configured = os.environ.get("COST_SOMA_HARNESS_STATE")
    if configured:
        return Path(configured)
    current = Path(__file__).resolve()
    for parent in current.parents:
        for name in STATE_NAMES:
            candidate = parent / ".codex" / name
            if candidate.exists():
                return candidate
    return None


def harness_state() -> dict[str, Any]:
    path = state_path()
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read().lstrip("\ufeff")
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def text_from_event(event: dict[str, Any]) -> str:
    candidates = [
        event.get("prompt"),
        event.get("last_assistant_message"),
        event.get("message"),
        event.get("user_prompt"),
        event.get("input"),
        event.get("text"),
    ]
    for item in candidates:
        if isinstance(item, str) and item.strip():
            return item
    return json.dumps(event, ensure_ascii=False)


def looks_like_policy_question(text: str) -> bool:
    return bool(POLICY_HINT_RE.search(text or ""))


def audit_dir() -> Path:
    state = harness_state()
    root = Path(
        os.environ.get(
            "COST_SOMA_AUDIT_DIR",
            state.get("audit_dir") or str(repo_root() / ".codex" / "cse-audit"),
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def repo_root() -> Path:
    configured = os.environ.get("COST_SOMA_REPO_ROOT")
    if configured:
        return Path(configured)
    path = state_path()
    if path:
        return path.resolve().parents[1]
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".codex").exists():
            return parent
    return current.parents[3]


def policy_tool_path() -> Path:
    state = harness_state()
    if state.get("policy_tool"):
        return Path(state["policy_tool"])
    if state.get("plugin_root"):
        return Path(state["plugin_root"]) / "scripts" / "policy_tool.py"
    return repo_root() / "scripts" / "policy_tool.py"


def python_path() -> str:
    state = harness_state()
    return str(state.get("python") or sys.executable)


def document_root() -> Path | None:
    state = harness_state()
    if state.get("document_root"):
        return Path(state["document_root"])
    if state.get("plugin_root"):
        return Path(state["plugin_root"]) / "document"
    return None


def write_audit(kind: str, payload: dict[str, Any]) -> None:
    record = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "kind": kind,
        **payload,
    }
    path = audit_dir() / "events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def emit_text(text: str) -> None:
    if text.strip():
        print(text)


def emit_hook_json(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def emit_user_prompt_context(context: str | None = None) -> None:
    payload: dict[str, Any] = {
        "continue": True,
        "suppressOutput": True,
    }
    if context and context.strip():
        payload["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    emit_hook_json(payload)


def emit_stop_result(system_message: str | None = None) -> None:
    payload: dict[str, Any] = {
        "continue": True,
        "suppressOutput": not bool(system_message and system_message.strip()),
    }
    if system_message and system_message.strip():
        payload["systemMessage"] = system_message
    emit_hook_json(payload)
