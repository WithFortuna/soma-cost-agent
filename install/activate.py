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
HOOK_FILES = ["harness_common.py", "user_prompt_submit.py", "stop_policy_review.py"]
AGENT_FILES = ["policy-evidence.toml", "policy-application.toml", "policy-reviewer.toml"]
HOOK_EVENT_SPECS = {
    "UserPromptSubmit": {
        "script": "user_prompt_submit.py",
        "timeout": 10,
        "statusMessage": "Checking Cost SOMA policy intent",
    },
    "Stop": {
        "script": "stop_policy_review.py",
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
    replacements = [
        ("python3 ../../install/activate.py", f"{python_cmd} {activate_cmd}"),
        ("python3 ../../install/deactivate.py", f"{python_cmd} {deactivate_cmd}"),
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
        "cost_soma",
        "cost-soma",
        "user_prompt_submit.py",
        "stop_policy_review.py",
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
    env["COST_SOMA_HARNESS_STATE"] = str(target / ".codex" / "cost-soma-policy-harness.json")
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


def activate(target: Path, skip_smoke: bool) -> None:
    require_python()
    assert_distribution_shape()
    if not target.exists() or not target.is_dir():
        fail(f"target must be an existing project directory: {target}")

    target = target.resolve()
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

    for name in HOOK_FILES:
        shutil.copy2(PLUGIN_ROOT / "hooks" / "scripts" / name, hooks_dir / name)

    for name in AGENT_FILES:
        src = PLUGIN_ROOT / "agents" / name
        text = transform_text(src.read_text(encoding="utf-8"), policy_tool=policy_tool, document_root=document_root, python=python)
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
        "audit_dir": str(codex_dir / "cost-soma-audit"),
        "installed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    state_path = codex_dir / "cost-soma-policy-harness.json"
    write_json(state_path, state)
    backup_path = merge_hooks(codex_dir / "hooks.json", hooks_dir, python)

    if not skip_smoke:
        run_smoke(target, state)

    print("Cost SOMA Policy Harness activated.")
    print(f"target: {target}")
    print(f"state: {state_path}")
    if backup_path:
        print(f"hooks backup: {backup_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Activate Cost SOMA Policy Harness in a local Codex project.")
    parser.add_argument("--target", required=True, help="Target Codex project directory.")
    parser.add_argument("--skip-smoke", action="store_true", help="Install without running policy_tool smoke checks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    activate(Path(args.target).expanduser(), args.skip_smoke)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
