#!/usr/bin/env python3
"""Render Cost SOMA evidence Markdown into a local HTML viewer."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

from policy_core import markdown_files, search_policy


DOC_FALLBACK = ["00-ai-guide.md", "04-board-support-items.md", "05-board-payment-methods.md", "06-board-evidence-documents.md"]
CORE_EVIDENCE_DOCS = ["04-board-support-items.md", "05-board-payment-methods.md", "06-board-evidence-documents.md"]
TEXT_EXTENSIONS = {".md", ".json", ".txt"}


def emit(payload: dict[str, Any], status: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return status


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def default_output_dir() -> Path:
    return Path.cwd() / "outputs" / "cost-soma-evidence" / timestamp()


def document_root() -> Path:
    configured = os.environ.get("COST_SOMA_DOCUMENT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "document"


def slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", value.strip()).strip("-").lower()
    return slug or "section"


def format_inline_text(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", lambda match: f"<code>{match.group(1)}</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def local_href(raw_href: str, base_dir: Path) -> str:
    parsed = urlparse(raw_href)
    if parsed.scheme in {"http", "https", "file", "mailto"}:
        return raw_href
    if raw_href.startswith("#"):
        return raw_href

    path_part, sep, fragment = raw_href.partition("#")
    decoded = unquote(path_part)
    target = (base_dir / decoded).resolve()
    if target.exists():
        href = target.as_uri()
    else:
        href = quote(raw_href, safe="/:#?&=%")
    if sep and target.exists():
        href = f"{href}#{quote(fragment)}"
    return href


def render_inline(text: str, base_dir: Path) -> str:
    pattern = re.compile(r"(!?)\[([^\]]*)\]\(([^)]+)\)")
    parts: list[str] = []
    cursor = 0
    for match in pattern.finditer(text):
        parts.append(format_inline_text(text[cursor : match.start()]))
        is_image, label, href = match.groups()
        resolved = local_href(href, base_dir)
        label_html = format_inline_text(label)
        if is_image:
            parts.append(
                f'<figure class="md-image"><img src="{html.escape(resolved, quote=True)}" '
                f'alt="{html.escape(label, quote=True)}"><figcaption>{label_html}</figcaption></figure>'
            )
        else:
            parts.append(f'<a href="{html.escape(resolved, quote=True)}">{label_html}</a>')
        cursor = match.end()
    parts.append(format_inline_text(text[cursor:]))
    return "".join(parts)


def is_table_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and set(stripped.replace("|", "").replace(":", "").replace("-", "").strip()) == set()


def split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def render_table(lines: list[str], base_dir: Path) -> str:
    rows = [split_table_row(line) for line in lines if not is_table_separator(line)]
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:]
    out = ["<div class=\"table-wrap\"><table>", "<thead><tr>"]
    out.extend(f"<th>{render_inline(cell, base_dir)}</th>" for cell in header)
    out.append("</tr></thead>")
    if body:
        out.append("<tbody>")
        for row in body:
            out.append("<tr>")
            out.extend(f"<td>{render_inline(cell, base_dir)}</td>" for cell in row)
            out.append("</tr>")
        out.append("</tbody>")
    out.append("</table></div>")
    return "\n".join(out)


def render_markdown(path: Path, highlight_lines: set[int]) -> str:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    base_dir = path.parent
    out: list[str] = []
    in_code = False
    code_lines: list[str] = []
    table_lines: list[str] = []

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
            code_lines = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            out.append(render_table(table_lines, base_dir))
            table_lines = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        is_hit = idx in highlight_lines
        wrapper_start = f'<div id="L{idx}" class="line{" hit" if is_hit else ""}" data-line="{idx}">'
        wrapper_end = "</div>"

        if stripped.startswith("```"):
            flush_table()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        if "|" in line and stripped.startswith("|"):
            table_lines.append(line)
            continue
        flush_table()

        if not stripped:
            out.append('<div class="blank"></div>')
            continue

        if stripped in {"<details>", "</details>"}:
            out.append(stripped)
            continue
        summary = re.fullmatch(r"<summary>(.*)</summary>", stripped)
        if summary:
            out.append(f"<summary>{render_inline(summary.group(1), base_dir)}</summary>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2)
            anchor = slugify(f"{path.stem}-{idx}-{text}")
            out.append(
                f'{wrapper_start}<h{level} id="{anchor}">{render_inline(text, base_dir)}</h{level}>{wrapper_end}'
            )
            continue

        quote_match = re.match(r"^>\s?(.*)$", stripped)
        if quote_match:
            out.append(f"{wrapper_start}<blockquote>{render_inline(quote_match.group(1), base_dir)}</blockquote>{wrapper_end}")
            continue

        list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if list_match:
            indent = min(len(list_match.group(1).replace("\t", "    ")) // 2, 6)
            marker = html.escape(list_match.group(2))
            text = list_match.group(3)
            out.append(
                f'{wrapper_start}<div class="list-item indent-{indent}"><span class="marker">{marker}</span> '
                f"{render_inline(text, base_dir)}</div>{wrapper_end}"
            )
            continue

        out.append(f"{wrapper_start}<p>{render_inline(stripped, base_dir)}</p>{wrapper_end}")

    flush_code()
    flush_table()
    return "\n".join(out)


def render_text_file(path: Path, highlight_lines: set[int]) -> str:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    rendered = []
    for idx, line in enumerate(lines, start=1):
        cls = "code-line hit" if idx in highlight_lines else "code-line"
        rendered.append(f'<span id="L{idx}" class="{cls}">{html.escape(line)}</span>')
    return "<pre><code>" + "\n".join(rendered) + "</code></pre>"


def selected_sources(results: list[dict[str, Any]], root: Path) -> list[Path]:
    by_name = {path.name: path for path in markdown_files()}
    names = list(dict.fromkeys(str(item.get("source", "")) for item in results if item.get("source")))
    if not names:
        names = DOC_FALLBACK
    else:
        for name in CORE_EVIDENCE_DOCS:
            if name not in names:
                names.append(name)
    paths: list[Path] = []
    for name in names:
        path = by_name.get(name) or root / name
        if path.exists() and path.suffix.lower() in TEXT_EXTENSIONS:
            paths.append(path)
    return paths


def highlight_map(results: list[dict[str, Any]], radius: int = 2) -> dict[str, set[int]]:
    mapping: dict[str, set[int]] = {}
    for item in results:
        source = str(item.get("source", ""))
        line = int(item.get("line_start") or 0)
        if not source or line <= 0:
            continue
        lines = mapping.setdefault(source, set())
        for candidate in range(max(1, line - radius), line + radius + 1):
            lines.add(candidate)
    return mapping


def html_page(*, question: str, category: str | None, results: list[dict[str, Any]], source_paths: list[Path], root: Path) -> str:
    highlights = highlight_map(results)
    rendered_sections: list[str] = []
    source_meta: list[dict[str, Any]] = []

    for path in source_paths:
        lines = highlights.get(path.name, set())
        body = render_markdown(path, lines) if path.suffix.lower() == ".md" else render_text_file(path, lines)
        rendered_sections.append(
            "\n".join(
                [
                    f'<section class="doc" id="{slugify(path.name)}">',
                    f"<header><h2>{html.escape(path.name)}</h2><p>{html.escape(str(path.relative_to(root) if path.is_relative_to(root) else path))}</p></header>",
                    body,
                    "</section>",
                ]
            )
        )
        source_meta.append(
            {
                "source": path.name,
                "path": str(path),
                "highlight_lines": sorted(lines),
            }
        )

    hit_items = []
    for item in results:
        source = str(item.get("source", ""))
        line = int(item.get("line_start") or 0)
        snippet = str(item.get("snippet", ""))
        hit_items.append(
            f'<li><a href="#{slugify(source)}">[{html.escape(source)}:{line}]</a> '
            f'<pre>{html.escape(snippet)}</pre></li>'
        )
    if not hit_items:
        hit_items.append("<li>검색 결과가 없어 핵심 문서를 기본으로 렌더링했습니다.</li>")

    nav_items = "\n".join(
        f'<li><a href="#{slugify(path.name)}">{html.escape(path.name)}</a></li>' for path in source_paths
    )
    hit_html = "\n".join(hit_items)
    source_json = html.escape(json.dumps(source_meta, ensure_ascii=False, indent=2))

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cost SOMA Evidence Viewer</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --paper: #ffffff;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d9dee7;
      --accent: #0f766e;
      --hit: #fff3bf;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    a {{ color: var(--accent); }}
    .layout {{ display: grid; grid-template-columns: minmax(260px, 320px) minmax(0, 1fr); min-height: 100vh; }}
    aside {{ position: sticky; top: 0; align-self: start; height: 100vh; overflow: auto; padding: 24px; border-right: 1px solid var(--line); background: #eef2f5; }}
    main {{ padding: 28px; }}
    h1 {{ font-size: 22px; line-height: 1.25; margin: 0 0 12px; }}
    h2 {{ font-size: 22px; margin: 0; }}
    h3, h4, h5, h6 {{ margin: 22px 0 8px; }}
    .meta {{ color: var(--muted); font-size: 13px; margin-bottom: 18px; }}
    .panel {{ border: 1px solid var(--line); border-radius: 8px; background: var(--paper); padding: 16px; margin: 0 0 18px; }}
    .panel ul {{ padding-left: 20px; }}
    .panel pre {{ white-space: pre-wrap; margin: 8px 0 14px; padding: 10px; background: #f8fafc; border: 1px solid var(--line); border-radius: 6px; font-size: 12px; }}
    .doc {{ background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 24px; margin-bottom: 24px; }}
    .doc header {{ border-bottom: 1px solid var(--line); margin: -4px 0 18px; padding-bottom: 12px; }}
    .doc header p {{ color: var(--muted); margin: 4px 0 0; }}
    .line {{ border-left: 4px solid transparent; padding-left: 10px; }}
    .line.hit, .code-line.hit {{ background: var(--hit); border-left-color: #eab308; }}
    .blank {{ height: 10px; }}
    p {{ margin: 8px 0; }}
    blockquote {{ margin: 8px 0; padding: 8px 12px; border-left: 4px solid var(--line); background: #f8fafc; }}
    details {{ margin: 12px 0; padding: 8px 12px; border: 1px solid var(--line); border-radius: 6px; }}
    summary {{ cursor: pointer; font-weight: 600; }}
    .list-item {{ display: grid; grid-template-columns: 42px 1fr; gap: 6px; margin: 5px 0; }}
    .marker {{ color: var(--muted); text-align: right; }}
    .indent-1 {{ margin-left: 18px; }} .indent-2 {{ margin-left: 36px; }} .indent-3 {{ margin-left: 54px; }}
    .indent-4 {{ margin-left: 72px; }} .indent-5 {{ margin-left: 90px; }} .indent-6 {{ margin-left: 108px; }}
    code {{ background: #eef2f5; border-radius: 4px; padding: 1px 4px; }}
    pre code {{ background: transparent; padding: 0; }}
    pre {{ overflow: auto; white-space: pre-wrap; }}
    .code-line {{ display: block; min-height: 1.4em; padding-left: 8px; border-left: 4px solid transparent; }}
    .table-wrap {{ overflow-x: auto; margin: 12px 0; }}
    table {{ border-collapse: collapse; min-width: 100%; }}
    th, td {{ border: 1px solid var(--line); padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; }}
    .md-image {{ margin: 12px 0; }}
    .md-image img {{ max-width: 100%; border: 1px solid var(--line); border-radius: 6px; background: #fff; }}
    .md-image figcaption {{ color: var(--muted); font-size: 12px; }}
    @media (max-width: 900px) {{
      .layout {{ display: block; }}
      aside {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
      main {{ padding: 16px; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside>
      <h1>Cost SOMA Evidence Viewer</h1>
      <div class="meta">Question: {html.escape(question)}<br>Category: {html.escape(category or "auto")}</div>
      <div class="panel">
        <strong>Documents</strong>
        <ul>{nav_items}</ul>
      </div>
      <div class="panel">
        <strong>Search hits</strong>
        <ul>{hit_html}</ul>
      </div>
      <details class="panel">
        <summary>Source metadata</summary>
        <pre>{source_json}</pre>
      </details>
    </aside>
    <main>
      {''.join(rendered_sections)}
    </main>
  </div>
</body>
</html>
"""


def render_view(question: str, category: str | None, limit: int, output_dir: Path) -> dict[str, Any]:
    root = document_root()
    search = search_policy(question, category=category, limit=limit)
    results = list(search.get("results", []))
    sources = selected_sources(results, root)
    output_dir.mkdir(parents=True, exist_ok=True)
    viewer_path = output_dir / "index.html"
    viewer_path.write_text(
        html_page(question=question, category=category, results=results, source_paths=sources, root=root),
        encoding="utf-8",
    )
    return {
        "ok": True,
        "command": "render-evidence-view",
        "question": question,
        "category": category,
        "viewer_path": str(viewer_path),
        "viewer_url": viewer_path.resolve().as_uri(),
        "sources": [
            {
                "source": path.name,
                "path": str(path),
                "highlight_lines": sorted(highlight_map(results).get(path.name, set())),
            }
            for path in sources
        ],
        "highlights": results,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render local Cost SOMA evidence documents as HTML. Outputs JSON only.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--category", default=None)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else default_output_dir()
    try:
        return emit(render_view(args.question, args.category, args.limit, output_dir))
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return emit({"ok": False, "command": "render-evidence-view", "error": str(exc)}, status=1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
