#!/usr/bin/env python3
"""JSON-only CLI for Cost SOMA policy harness scripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from policy_core import (
    classify_expense_item,
    docs_for_category,
    form_for_question,
    get_required_documents,
    list_policy_form_templates,
    prepare_policy_form_packet,
    search_policy,
    validate_form_artifacts,
    validate_policy_answer,
)


def emit(payload: dict[str, Any], status: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return status


def read_answer(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def read_json_arg(value: str | None, path: str | None = None) -> dict[str, Any]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not value:
        return {}
    return json.loads(value)


def cmd_classify(args: argparse.Namespace) -> dict[str, Any]:
    payload = classify_expense_item(args.question)
    if args.max_candidates is not None:
        payload["candidates"] = payload.get("candidates", [])[: args.max_candidates]
    return {"ok": True, "command": "classify", **payload}


def cmd_search(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "ok": True,
        "command": "search",
        "query": args.query,
        "category": args.category,
        "results": search_policy(args.query, category=args.category, limit=args.limit),
    }


def cmd_docs(args: argparse.Namespace) -> dict[str, Any]:
    return {"ok": True, "command": "docs", **docs_for_category(args.category)}


def cmd_form(args: argparse.Namespace) -> dict[str, Any]:
    return {"ok": True, "command": "form", **form_for_question(args.question, category=args.category)}


def cmd_templates(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "ok": True,
        "command": "templates",
        **list_policy_form_templates(category=args.category, stage=args.stage),
    }


def cmd_form_packet(args: argparse.Namespace) -> dict[str, Any]:
    known_values = read_json_arg(args.known_values_json, args.known_values_file)
    return {
        "ok": True,
        "command": "form-packet",
        **prepare_policy_form_packet(
            question=args.question,
            category=args.category,
            stage=args.stage,
            payment_method=args.payment_method,
            known_values=known_values,
        ),
    }


def cmd_validate_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    form_packet = read_json_arg(args.form_packet_json, args.form_packet_file)
    return {
        "ok": True,
        "command": "validate-artifacts",
        **validate_form_artifacts(form_packet, args.artifact),
    }


def cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
    answer = read_answer(args.answer_file)
    return {"ok": True, "command": "validate", **validate_policy_answer(args.question, answer)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cost SOMA policy helper. Outputs JSON only.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser("classify")
    classify.add_argument("--question", required=True)
    classify.add_argument("--max-candidates", type=int, default=None)
    classify.set_defaults(func=cmd_classify)

    search = subparsers.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--category", default=None)
    search.add_argument("--limit", type=int, default=8)
    search.set_defaults(func=cmd_search)

    docs = subparsers.add_parser("docs")
    docs.add_argument("--category", required=True)
    docs.set_defaults(func=cmd_docs)

    form = subparsers.add_parser("form")
    form.add_argument("--question", required=True)
    form.add_argument("--category", default=None)
    form.set_defaults(func=cmd_form)

    templates = subparsers.add_parser("templates")
    templates.add_argument("--category", default=None)
    templates.add_argument("--stage", default=None)
    templates.set_defaults(func=cmd_templates)

    form_packet = subparsers.add_parser("form-packet")
    form_packet.add_argument("--question", required=True)
    form_packet.add_argument("--category", default=None)
    form_packet.add_argument("--stage", default="auto")
    form_packet.add_argument("--payment-method", default=None)
    form_packet.add_argument("--known-values-json", default=None)
    form_packet.add_argument("--known-values-file", default=None)
    form_packet.set_defaults(func=cmd_form_packet)

    validate_artifacts = subparsers.add_parser("validate-artifacts")
    validate_artifacts.add_argument("--form-packet-json", default=None)
    validate_artifacts.add_argument("--form-packet-file", default=None)
    validate_artifacts.add_argument("--artifact", action="append", default=[])
    validate_artifacts.set_defaults(func=cmd_validate_artifacts)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--question", required=True)
    validate.add_argument("--answer-file", required=True)
    validate.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return emit(args.func(args))
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return emit({"ok": False, "command": args.command, "error": str(exc)}, status=1)


if __name__ == "__main__":
    raise SystemExit(main())
