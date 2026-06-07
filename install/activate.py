#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
STATE_NAME = "cse-policy-harness.json"
LEGACY_STATE_NAMES = ["cost-soma-policy-harness.json"]
HOOK_FILES = ["cse-harness-common.py", "cse-user-prompt-submit.py", "cse-stop-policy-review.py"]
LEGACY_HOOK_FILES = ["harness_common.py", "user_prompt_submit.py", "stop_policy_review.py"]
AGENT_FILES = ["cse-policy-evidence.toml", "cse-policy-application.toml", "cse-policy-reviewer.toml"]
LEGACY_AGENT_FILES = ["policy-evidence.toml", "policy-application.toml", "policy-reviewer.toml"]
DEFAULT_MODEL = "gpt-5.5"
INTERACTIVE_MODEL_CHOICES = [
    ("gpt-5.5", "recommended; strongest for evidence-heavy policy reasoning"),
    ("gpt-5.4-mini", "faster and lower cost for lighter policy checks"),
]
HOOK_EVENT_SPECS = {
    "UserPromptSubmit": {
        "script": "cse-user-prompt-submit.py",
        "timeout": 10,
        "statusMessage": "Checking Cost SOMA policy intent",
    },
    "Stop": {
        "script": "cse-stop-policy-review.py",
        "timeout": 15,
        "statusMessage": "Auditing Cost SOMA policy answer",
    },
}


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def require_python() -> None:
    if sys.version_info < (3, 10):
        fail("Python 3.10+ is required. On macOS, install it with: brew install python")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_path = path.with_name(path.name + f".bak-{timestamp()}")
    shutil.copy2(path, backup_path)
    return backup_path


def normalize_model(value: str | None) -> str:
    model = (value or "").strip()
    if not model:
        fail("model must not be empty")
    if any(char in model for char in "\r\n\t"):
        fail("model must be a single-line model id")
    if len(model) > 160:
        fail("model id is unexpectedly long")
    return model


def choose_model_interactively() -> str:
    if not sys.stdin.isatty():
        return DEFAULT_MODEL

    print("Choose the Cost SOMA custom-agent model:")
    for index, (model, description) in enumerate(INTERACTIVE_MODEL_CHOICES, start=1):
        print(f"  {index}) {model} - {description}")
    print("  3) custom model id")

    while True:
        raw_choice = input(f"Model [1: {DEFAULT_MODEL}]: ").strip()
        if not raw_choice:
            return DEFAULT_MODEL
        if raw_choice in {"1", INTERACTIVE_MODEL_CHOICES[0][0]}:
            return INTERACTIVE_MODEL_CHOICES[0][0]
        if raw_choice in {"2", INTERACTIVE_MODEL_CHOICES[1][0]}:
            return INTERACTIVE_MODEL_CHOICES[1][0]
        if raw_choice == "3":
            return normalize_model(input("Custom model id: "))
        if raw_choice.startswith("gpt-") or "/" in raw_choice or ":" in raw_choice:
            return normalize_model(raw_choice)
        print("Choose 1, 2, 3, or enter a model id.")


def resolve_model(model: str | None) -> str:
    if model is not None:
        return normalize_model(model)
    return choose_model_interactively()


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def inject_agent_model(text: str, model: str) -> str:
    model_line = f"model = {toml_string(model)}"
    lines = text.splitlines()
    for index, line in enumerate(lines):
        parts = line.split("=", 1)
        if len(parts) == 2 and parts[0].strip() == "model":
            lines[index] = model_line
            return "\n".join(lines) + ("\n" if text.endswith("\n") else "")

    insert_at = 0
    for index, line in enumerate(lines):
        parts = line.split("=", 1)
        if len(parts) == 2:
            key = parts[0].strip()
            if key == "description":
                insert_at = index + 1
                break
            if key == "name":
                insert_at = index + 1
    lines.insert(insert_at, model_line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")

def assert_distribution_shape() -> None:
    required = [
        PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
        PLUGIN_ROOT / "scripts" / "policy_tool.py",
        PLUGIN_ROOT / "scripts" / "policy_core.py",
        PLUGIN_ROOT / "scripts" / "policy_engine.py",
        PLUGIN_ROOT / "document" / "rules.json",
        PLUGIN_ROOT / "document" / "assets",
        PLUGIN_ROOT / "document" / "extracted",
        PLUGIN_ROOT / "hooks" / "scripts",
        PLUGIN_ROOT / "agents",
        PLUGIN_ROOT / "skills",
    ]
    for path in required:
        if not path.exists():
            fail(f"missing required distribution path: {path}")
    forbidden = [PLUGIN_ROOT / ("m" + "cp"), PLUGIN_ROOT / ("." + "m" + "cp.json")]
    for path in forbidden:
        if path.exists():
            fail(f"MCP runtime artifact must not be present in Mac distribution: {path}")


def transform_text(text: str, *, policy_tool: Path, document_root: Path, python: str) -> str:
    plugin_root = policy_tool.resolve().parents[1]
    python_cmd = shlex.quote(python)
    tool_cmd = shlex.quote(str(policy_tool))
    activate_cmd = shlex.quote(str(plugin_root / "install" / "activate.py"))
    deactivate_cmd = shlex.quote(str(plugin_root / "install" / "deactivate.py"))
    viewer_cmd = shlex.quote(str(plugin_root / "scripts" / "render_evidence_view.py"))
    replacements = [
        ("python3 ../../install/activate.py", f"{python_cmd} {activate_cmd}"),
        ("python3 ../../install/deactivate.py", f"{python_cmd} {deactivate_cmd}"),
        ("python3 ../../scripts/render_evidence_view.py", f"{python_cmd} {viewer_cmd}"),
        ("python3 scripts/render_evidence_view.py", f"{python_cmd} {viewer_cmd}"),
        ("python3 scripts/policy_tool.py", f"{python_cmd} {tool_cmd}"),
        ("cost-soma-policy-harness/scripts/policy_tool.py", str(policy_tool)),
        ("document/rules.json and document/*.md", f"{document_root / 'rules.json'} and {document_root}/*.md"),
        ("document/rules.json", str(document_root / "rules.json")),
        ("document/*.md", f"{document_root}/*.md"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def copy_text_tree(
    src: Path,
    dst: Path,
    *,
    allowed_root: Path,
    policy_tool: Path,
    document_root: Path,
    python: str,
) -> None:
    if dst.exists():
        resolved_dst = dst.resolve()
        resolved_root = allowed_root.resolve()
        if resolved_dst != resolved_root and resolved_root not in resolved_dst.parents:
            fail(f"refusing to replace path outside target skills directory: {dst}")
        shutil.rmtree(resolved_dst)
    for src_file in src.rglob("*"):
        rel = src_file.relative_to(src)
        dst_file = dst / rel
        if src_file.is_dir():
            dst_file.mkdir(parents=True, exist_ok=True)
            continue
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        if src_file.suffix.lower() in {".md", ".toml", ".json", ".py", ".txt"}:
            text = src_file.read_text(encoding="utf-8")
            dst_file.write_text(
                transform_text(text, policy_tool=policy_tool, document_root=document_root, python=python),
                encoding="utf-8",
            )
        else:
            shutil.copy2(src_file, dst_file)


def is_cost_soma_hook(entry: Any) -> bool:
    text = json.dumps(entry, ensure_ascii=False)
    markers = [
        "Cost SOMA",
        "COST_SOMA_HARNESS_STATE",
        STATE_NAME,
        "cse-user-prompt-submit.py",
        "cse-stop-policy-review.py",
        "cost-soma-policy-harness-mac",
        "soma-cost-agent",
    ]
    return any(marker in text for marker in markers)


def merge_hooks(hooks_json_path: Path, hook_dir: Path, python: str) -> Path | None:
    existing = read_json(hooks_json_path) if hooks_json_path.exists() else {}
    if not isinstance(existing.get("hooks"), dict):
        existing["hooks"] = {}
    backup_path = backup(hooks_json_path)

    hooks = existing["hooks"]
    for event, spec in HOOK_EVENT_SPECS.items():
        current = hooks.get(event, [])
        if not isinstance(current, list):
            current = []
        current = [entry for entry in current if not is_cost_soma_hook(entry)]
        command = f"{shlex.quote(python)} {shlex.quote(str(hook_dir / spec['script']))}"
        current.append(
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "timeout": spec["timeout"],
                        "statusMessage": spec["statusMessage"],
                    }
                ]
            }
        )
        hooks[event] = current

    write_json(hooks_json_path, existing)
    return backup_path


def run_smoke(target: Path, state: dict[str, str]) -> None:
    env = os.environ.copy()
    env["COST_SOMA_DOCUMENT_ROOT"] = state["document_root"]
    env["COST_SOMA_HARNESS_STATE"] = str(target / ".codex" / STATE_NAME)
    commands = [
        [state["python"], state["policy_tool"], "classify", "--question", "Aws사용하러는데 뭐해야함"],
        [state["python"], state["policy_tool"], "form", "--question", "맥북용 허브독 사려고함"],
        [
            state["python"],
            state["policy_tool"],
            "form-packet",
            "--question",
            "구매대행 신청서 만들어줘",
            "--category",
            "material_purchase",
            "--stage",
            "application",
        ],
    ]
    for command in commands:
        proc = subprocess.run(command, cwd=target, env=env, text=True, capture_output=True, check=False)
        if proc.returncode != 0:
            fail(f"smoke command failed: {' '.join(command)}\n{proc.stderr or proc.stdout}")
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            fail(f"smoke command returned non-JSON output: {exc}\n{proc.stdout[:500]}")
        if not payload.get("ok", True):
            fail(f"smoke command returned ok=false: {payload}")


def activate(target: Path, skip_smoke: bool, model: str | None) -> None:
    require_python()
    assert_distribution_shape()
    if not target.exists() or not target.is_dir():
        fail(f"target must be an existing project directory: {target}")

    target = target.resolve()
    configured_model = resolve_model(model)
    policy_tool = PLUGIN_ROOT / "scripts" / "policy_tool.py"
    document_root = PLUGIN_ROOT / "document"
    python = str(Path(sys.executable).resolve())

    codex_dir = target / ".codex"
    hooks_dir = codex_dir / "hooks"
    agents_dir = codex_dir / "agents"
    agent_skills_dir = target / ".agents" / "skills"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_skills_dir.mkdir(parents=True, exist_ok=True)

    for name in LEGACY_HOOK_FILES:
        path = hooks_dir / name
        if path.exists() and path.is_file():
            path.unlink()
    for name in LEGACY_AGENT_FILES:
        path = agents_dir / name
        if path.exists() and path.is_file():
            path.unlink()
    for name in LEGACY_STATE_NAMES:
        path = codex_dir / name
        if path.exists() and path.is_file():
            path.unlink()

    for name in HOOK_FILES:
        shutil.copy2(PLUGIN_ROOT / "hooks" / "scripts" / name, hooks_dir / name)

    for name in AGENT_FILES:
        src = PLUGIN_ROOT / "agents" / name
        text = transform_text(src.read_text(encoding="utf-8"), policy_tool=policy_tool, document_root=document_root, python=python)
        text = inject_agent_model(text, configured_model)
        (agents_dir / name).write_text(text, encoding="utf-8")

    for src_skill in sorted((PLUGIN_ROOT / "skills").glob("cost-soma-*")):
        if src_skill.is_dir():
            copy_text_tree(
                src_skill,
                agent_skills_dir / src_skill.name,
                allowed_root=agent_skills_dir,
                policy_tool=policy_tool,
                document_root=document_root,
                python=python,
            )

    state = {
        "plugin_root": str(PLUGIN_ROOT),
        "document_root": str(document_root),
        "policy_tool": str(policy_tool),
        "python": python,
        "model": configured_model,
        "audit_dir": str(codex_dir / "cse-audit"),
        "installed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    state_path = codex_dir / STATE_NAME
    write_json(state_path, state)
    backup_path = merge_hooks(codex_dir / "hooks.json", hooks_dir, python)

    if not skip_smoke:
        run_smoke(target, state)

    print("Cost SOMA Policy Harness activated.")
    print(f"target: {target}")
    print(f"state: {state_path}")
    print(f"model: {configured_model}")
    if backup_path:
        print(f"hooks backup: {backup_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Activate Cost SOMA Policy Harness in a local Codex project.")
    parser.add_argument("--target", required=True, help="Target Codex project directory.")
    parser.add_argument(
        "--model",
        help=f"Cost SOMA custom-agent model to pin. Defaults to an interactive prompt in a TTY, otherwise {DEFAULT_MODEL}.",
    )
    parser.add_argument("--skip-smoke", action="store_true", help="Install without running policy_tool smoke checks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    activate(Path(args.target).expanduser(), args.skip_smoke, args.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
