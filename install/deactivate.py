#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any


STATE_NAMES = ["cse-policy-harness.json", "cost-soma-policy-harness.json"]
HOOK_FILES = [
    "cse-harness-common.py",
    "cse-user-prompt-submit.py",
    "cse-stop-policy-review.py",
    "harness_common.py",
    "user_prompt_submit.py",
    "stop_policy_review.py",
]
AGENT_FILES = [
    "cse-policy-evidence.toml",
    "cse-policy-application.toml",
    "cse-policy-reviewer.toml",
    "policy-evidence.toml",
    "policy-application.toml",
    "policy-reviewer.toml",
]


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_path = path.with_name(path.name + f".bak-{timestamp()}")
    shutil.copy2(path, backup_path)
    return backup_path


def is_cost_soma_hook(entry: Any) -> bool:
    text = json.dumps(entry, ensure_ascii=False)
    markers = [
        "Cost SOMA",
        "COST_SOMA_HARNESS_STATE",
        "cse-policy-harness.json",
        "cost-soma-policy-harness.json",
        "cse-user-prompt-submit.py",
        "cse-stop-policy-review.py",
        "cost-soma-policy-harness-mac",
        "soma-cost-agent",
    ]
    return any(marker in text for marker in markers)


def remove_hooks(hooks_json_path: Path) -> Path | None:
    if not hooks_json_path.exists():
        return None
    payload = read_json(hooks_json_path)
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        return None
    backup_path = backup(hooks_json_path)
    for event, entries in list(hooks.items()):
        if isinstance(entries, list):
            hooks[event] = [entry for entry in entries if not is_cost_soma_hook(entry)]
    write_json(hooks_json_path, payload)
    return backup_path


def remove_file(path: Path) -> None:
    if path.exists() and path.is_file():
        path.unlink()


def remove_dir(path: Path, root: Path) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    if root.resolve() not in resolved.parents and resolved != root.resolve():
        fail(f"refusing to remove path outside target: {path}")
    shutil.rmtree(resolved)


def deactivate(target: Path) -> None:
    if not target.exists() or not target.is_dir():
        fail(f"target must be an existing project directory: {target}")
    target = target.resolve()

    codex_dir = target / ".codex"
    hooks_dir = codex_dir / "hooks"
    agents_dir = codex_dir / "agents"
    skills_dir = target / ".agents" / "skills"

    backup_path = remove_hooks(codex_dir / "hooks.json")

    for name in HOOK_FILES:
        remove_file(hooks_dir / name)
    for name in AGENT_FILES:
        remove_file(agents_dir / name)
    for skill in skills_dir.glob("cost-soma-*"):
        if skill.is_dir():
            remove_dir(skill, target)

    for name in STATE_NAMES:
        remove_file(codex_dir / name)

    print("Cost SOMA Policy Harness deactivated.")
    print(f"target: {target}")
    if backup_path:
        print(f"hooks backup: {backup_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deactivate Cost SOMA Policy Harness from a local Codex project.")
    parser.add_argument("--target", required=True, help="Target Codex project directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    deactivate(Path(args.target).expanduser())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
