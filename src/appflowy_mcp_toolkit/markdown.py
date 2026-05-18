"""Minimal Markdown-to-SerdeBlock converter for AppFlowy page appends.

Converts a subset of Markdown to AppFlowy SerdeBlock dicts that can be
passed to the append-block API route.  Block types are confirmed from
AppFlowy-Cloud upstream fixture files in:
  libs/workspace-template/assets/initial_document.json
  libs/workspace-template/assets/desktop_guide.json
  libs/workspace-template/assets/mobile_guide.json

Supported:
  - paragraphs          → type "paragraph"
  - headings # – ######  → type "heading" with data.level 1–6
  - unordered list items (- / * / + at start) → type "bulleted_list"
  - ordered list items (N. at start)           → type "numbered_list"
  - blockquote (> prefix)                      → type "quote"
  - blank lines split blocks

Inline text is kept as plain text (single delta insert).
Rich inline formatting (bold, italic, code span, links) is NOT converted;
the raw Markdown syntax characters are preserved in the insert text.
This is intentional and documented: full rich-inline conversion is backlog.
"""

from __future__ import annotations

import re
from typing import Any

# Regex patterns for block-level detection
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")
_UNORDERED_RE = re.compile(r"^[-*+]\s+(.*)")
_ORDERED_RE = re.compile(r"^\d+\.\s+(.*)")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)")


def _delta(text: str) -> list[dict[str, Any]]:
    """Return a minimal single-insert delta for plain text."""
    return [{"insert": text}]


def _block(
    block_type: str,
    text: str,
    extra_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {"delta": _delta(text)}
    if extra_data:
        data.update(extra_data)
    return {"type": block_type, "data": data, "children": []}


def markdown_to_blocks(markdown: str) -> list[dict[str, Any]]:
    """Convert a Markdown string to a list of AppFlowy SerdeBlock dicts.

    Raises ValueError if the input is empty or whitespace-only.
    """
    if not markdown or not markdown.strip():
        raise ValueError("Markdown input must not be empty or whitespace-only")

    blocks: list[dict[str, Any]] = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        # Blank line → skip (paragraph breaks are implicit in Markdown;
        # each non-blank line becomes its own block here)
        if not line.strip():
            continue

        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            blocks.append(_block("heading", text, {"level": level}))
            continue

        m = _UNORDERED_RE.match(line)
        if m:
            blocks.append(_block("bulleted_list", m.group(1).strip()))
            continue

        m = _ORDERED_RE.match(line)
        if m:
            blocks.append(_block("numbered_list", m.group(1).strip()))
            continue

        m = _BLOCKQUOTE_RE.match(line)
        if m:
            blocks.append(_block("quote", m.group(1).strip()))
            continue

        # Default: paragraph
        blocks.append(_block("paragraph", line.strip()))

    if not blocks:
        raise ValueError("Markdown produced no blocks (input may be blank-lines only)")

    return blocks
