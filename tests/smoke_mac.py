#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


DIST_ROOT = Path(__file__).resolve().parents[1]
STATE_NAME = "cse-policy-harness.json"
TEXT_SUFFIXES = {".json", ".md", ".py", ".toml", ".txt", ".yml", ".yaml", ".sh"}
FORBIDDEN_TEXT = ["/mnt" + "/c", "C:" + "\\", "mcp" + "Servers", "cost_soma_policy" + "_mcp"]
REQUIRED_TARGET_FILES = [
    ".codex/hooks.json",
    ".codex/hooks/cse-harness-common.py",
    ".codex/hooks/cse-user-prompt-submit.py",
    ".codex/hooks/cse-stop-policy-review.py",
    ".codex/agents/cse-policy-evidence.toml",
    ".codex/agents/cse-policy-application.toml",
    ".codex/agents/cse-policy-reviewer.toml",
    ".agents/skills/cost-soma-policy-orchestrator/SKILL.md",
    ".agents/skills/cost-soma-evidence/SKILL.md",
    ".agents/skills/cost-soma-application/SKILL.md",
    ".agents/skills/cost-soma-answer-review/SKILL.md",
    ".agents/skills/cost-soma-evidence-viewer/SKILL.md",
    ".agents/skills/cost-soma-activate-project/SKILL.md",
    ".agents/skills/cost-soma-deactivate-project/SKILL.md",
]
FORBIDDEN_TARGET_FILES = [
    ".codex/hooks/harness_common.py",
    ".codex/hooks/user_prompt_submit.py",
    ".codex/hooks/stop_policy_review.py",
    ".codex/agents/policy-evidence.toml",
    ".codex/agents/policy-application.toml",
    ".codex/agents/policy-reviewer.toml",
    ".codex/cost-soma-policy-harness.json",
]


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")


def assert_exists(path: Path) -> None:
    if not path.exists():
        fail(f"missing required path: {path}")


def scan_distribution() -> None:
    assert_exists(DIST_ROOT / ".codex-plugin" / "plugin.json")
    assert_exists(DIST_ROOT / "document" / "rules.json")
    assert_exists(DIST_ROOT / "document" / "assets")
    assert_exists(DIST_ROOT / "document" / "extracted")
    if (DIST_ROOT / ("m" + "cp")).exists() or (DIST_ROOT / ("." + "m" + "cp.json")).exists():
        fail("Mac distribution must not include MCP runtime files")

    for path in DIST_ROOT.rglob("*"):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.name in {".DS_Store", "." + "m" + "cp.json"} or ("m" + "cp") in path.parts:
            fail(f"forbidden runtime path in distribution: {path.relative_to(DIST_ROOT)}")
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in FORBIDDEN_TEXT:
            if marker in text:
                fail(f"forbidden text marker {marker!r} in {path.relative_to(DIST_ROOT)}")


def load_state(target: Path) -> dict[str, str]:
    state_path = target / ".codex" / STATE_NAME
    assert_exists(state_path)
    payload = read_json(state_path)
    required = ["plugin_root", "document_root", "policy_tool", "python"]
    missing = [key for key in required if not payload.get(key)]
    if missing:
        fail(f"state file missing keys: {', '.join(missing)}")
    return {key: str(value) for key, value in payload.items()}


def run_json(command: list[str], *, cwd: Path, env: dict[str, str], stdin: str | None = None) -> dict[str, Any]:
    proc = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"command failed: {' '.join(command)}\n{proc.stderr or proc.stdout}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"command returned non-JSON output: {exc}\n{proc.stdout[:1000]}")


def assert_hook_command_is_unix(target: Path) -> None:
    hooks = read_json(target / ".codex" / "hooks.json").get("hooks", {})
    text = json.dumps(hooks, ensure_ascii=False)
    if "/mnt" + "/c" in text or "C:" + "\\" in text:
        fail("installed hook command contains a WSL or Windows path")
    if "cse-user-prompt-submit.py" not in text or "cse-stop-policy-review.py" not in text:
        fail("installed hooks.json does not reference Cost SOMA hook scripts")
    for legacy in ["user_prompt_submit.py", "stop_policy_review.py"]:
        if legacy in text:
            fail(f"installed hooks.json still references legacy hook script: {legacy}")


def check_target_layout(target: Path) -> None:
    for rel in REQUIRED_TARGET_FILES:
        assert_exists(target / rel)
    for rel in FORBIDDEN_TARGET_FILES:
        if (target / rel).exists():
            fail(f"legacy unprefixed runtime file should not remain: {rel}")
    assert_hook_command_is_unix(target)
    activate_skill = (target / ".agents/skills/cost-soma-activate-project/SKILL.md").read_text(encoding="utf-8")
    deactivate_skill = (target / ".agents/skills/cost-soma-deactivate-project/SKILL.md").read_text(encoding="utf-8")
    if "../../install/activate.py" in activate_skill or "../../install/deactivate.py" in deactivate_skill:
        fail("installed activator skills still contain relative installer paths")
    if "install/activate.py" not in activate_skill or "install/deactivate.py" not in deactivate_skill:
        fail("installed activator skills do not reference installer scripts")


def check_policy_tool(target: Path, state: dict[str, str]) -> None:
    python = state["python"]
    tool = state["policy_tool"]
    document_root = state["document_root"]
    assert_exists(Path(tool))
    assert_exists(Path(document_root) / "rules.json")

    env = os.environ.copy()
    env["COST_SOMA_DOCUMENT_ROOT"] = document_root
    env["COST_SOMA_HARNESS_STATE"] = str(target / ".codex" / STATE_NAME)

    for question in ["Aws사용하러는데 뭐해야함", "맥북용 허브독 사려고함", "디자인 외주 맡기려고해"]:
        payload = run_json([python, tool, "classify", "--question", question], cwd=target, env=env)
        if not payload.get("ok") or not payload.get("candidates"):
            fail(f"classify smoke failed for question: {question}")

    form = run_json([python, tool, "form", "--question", "맥북용 허브독 사려고함"], cwd=target, env=env)
    if not form.get("writing_format_text"):
        fail("form smoke did not return writing_format_text")

    packet = run_json(
        [
            python,
            tool,
            "form-packet",
            "--question",
            "구매대행 신청서 만들어줘",
            "--category",
            "material_purchase",
            "--stage",
            "application",
        ],
        cwd=target,
        env=env,
    )
    for key in ["templates", "missing_required_fields", "artifact_instructions"]:
        if key not in packet:
            fail(f"form-packet smoke missing key: {key}")


def check_evidence_viewer(target: Path, state: dict[str, str]) -> None:
    python = state["python"]
    plugin_root = Path(state["plugin_root"])
    viewer_script = plugin_root / "scripts" / "render_evidence_view.py"
    assert_exists(viewer_script)

    env = os.environ.copy()
    env["COST_SOMA_DOCUMENT_ROOT"] = state["document_root"]
    env["COST_SOMA_HARNESS_STATE"] = str(target / ".codex" / STATE_NAME)
    output_dir = target / "outputs" / "cost-soma-evidence-smoke"
    payload = run_json(
        [
            python,
            str(viewer_script),
            "--question",
            "라즈베리파이와 허브 구매 가능해?",
            "--category",
            "material_purchase",
            "--output-dir",
            str(output_dir),
        ],
        cwd=target,
        env=env,
    )
    viewer_path = Path(str(payload.get("viewer_path", "")))
    assert_exists(viewer_path)
    html = viewer_path.read_text(encoding="utf-8")
    for marker in ["Cost SOMA Evidence Viewer", "04-board-support-items.md", "라즈베리파이", "class=\"line hit\""]:
        if marker not in html:
            fail(f"evidence viewer HTML missing marker: {marker}")
    if not payload.get("viewer_url", "").startswith("file://"):
        fail("evidence viewer did not return a file:// viewer_url")


def check_hooks(target: Path, state: dict[str, str]) -> None:
    env = os.environ.copy()
    env["COST_SOMA_HARNESS_STATE"] = str(target / ".codex" / STATE_NAME)
    env["COST_SOMA_DOCUMENT_ROOT"] = state["document_root"]

    prompt_payload = run_json(
        [state["python"], str(target / ".codex" / "hooks" / "cse-user-prompt-submit.py")],
        cwd=target,
        env=env,
        stdin=json.dumps({"prompt": "디자인 외주 맡기려고해"}, ensure_ascii=False),
    )
    context = prompt_payload.get("hookSpecificOutput", {}).get("additionalContext", "")
    if "cse-policy-evidence" not in context or "cse-policy-application" not in context or state["policy_tool"] not in context:
        fail("UserPromptSubmit hook did not inject team-mode policy context")

    neutral_payload = run_json(
        [state["python"], str(target / ".codex" / "hooks" / "cse-user-prompt-submit.py")],
        cwd=target,
        env=env,
        stdin=json.dumps({"prompt": "오늘 날씨 어때"}, ensure_ascii=False),
    )
    if neutral_payload.get("hookSpecificOutput"):
        fail("UserPromptSubmit hook injected context for a non-policy prompt")

    stop_payload = run_json(
        [state["python"], str(target / ".codex" / "hooks" / "cse-stop-policy-review.py")],
        cwd=target,
        env=env,
        stdin=json.dumps(
            {
                "question": "디자인 외주 맡기려고해",
                "last_assistant_message": "가능합니다.",
            },
            ensure_ascii=False,
        ),
    )
    if "systemMessage" not in stop_payload or not isinstance(stop_payload.get("systemMessage"), str):
        fail("Stop hook did not return a systemMessage for an incomplete policy answer")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test an activated Cost SOMA Policy Harness target project.")
    parser.add_argument("--target", required=True, help="Target Codex project directory activated by install/activate.py.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        fail(f"target must be an existing directory: {target}")

    scan_distribution()
    check_target_layout(target)
    state = load_state(target)
    check_policy_tool(target, state)
    check_evidence_viewer(target, state)
    check_hooks(target, state)

    print("Cost SOMA Mac harness smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
