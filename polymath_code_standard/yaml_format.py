# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""YAML formatter with matrix-preserving flow sequence support.

Wraps yamlfix for standard formatting (--- header, true/false normalisation,
indentation) and adds a post-pass that restores N-per-row flow sequences
(matrices) that would otherwise be collapsed to a single long line.

A "matrix" is a flow sequence (bracket-enclosed) whose items were written
across multiple lines with a consistent number of items per row:

    covariance: [1e-4, 0.0,  0.0,
                 0.0,  1e-4, 0.0,
                 0.0,  0.0,  1e-4]

The formatter preserves the N-per-row structure, fixes indentation so
continuation lines align with the first item after '[', and pads each column
to the width of its widest value.

Raises ValueError if a multi-line flow sequence has inconsistent row sizes
(e.g. 3 on the first line but 2 on the second).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ruyaml import YAML
from ruyaml.comments import CommentedMap, CommentedSeq
from yamlfix import fix_code
from yamlfix.model import YamlfixConfig, YamlNodeStyle

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    return yaml


def _yamlfix_config() -> YamlfixConfig:
    config = YamlfixConfig()
    config.sequence_style = YamlNodeStyle.KEEP_STYLE
    config.line_length = 256
    config.whitelines = 1
    return config


# ---------------------------------------------------------------------------
# Pre-pass: detect matrix sequences in the original source
# ---------------------------------------------------------------------------


def _walk_matrices(
    node: Any,
    path: str,
    matrices: dict[str, int],
    errors: list[str],
) -> None:
    if isinstance(node, CommentedMap):
        for key, value in node.items():
            child_path = f'{path}.{key}' if path else str(key)
            _walk_matrices(value, child_path, matrices, errors)
    elif isinstance(node, CommentedSeq):
        if node.fa.flow_style():
            n = len(node)
            if n <= 1:
                return
            item_lines = [node.lc.item(i)[0] for i in range(n)]
            # Single-line sequence — leave to yamlfix
            if item_lines[0] == item_lines[-1]:
                return
            # Multi-line: group consecutive same-line items into rows
            rows: list[list[int]] = [[0]]
            for i in range(1, n):
                if item_lines[i] == item_lines[i - 1]:
                    rows[-1].append(i)
                else:
                    rows.append([i])
            row_sizes = [len(r) for r in rows]
            items_per_row = row_sizes[0]
            # All rows except possibly the last must have items_per_row items
            for size in row_sizes[:-1]:
                if size != items_per_row:
                    errors.append(f"Irregular matrix at '{path}': row sizes are {row_sizes}")
                    return
            if row_sizes[-1] > items_per_row:
                errors.append(
                    f"Irregular matrix at '{path}': last row has {row_sizes[-1]} items "
                    f'but first row has {items_per_row}'
                )
                return
            matrices[path] = items_per_row
        else:
            # Block sequence: recurse into items (may contain nested maps with matrices)
            for i, item in enumerate(node):
                _walk_matrices(item, f'{path}[{i}]', matrices, errors)


def detect_matrices(source: str) -> dict[str, int]:
    """Return {yaml_path: items_per_row} for all matrix flow sequences in source.

    Raises ValueError listing all irregular multi-line flow sequences found.
    """
    yaml = _make_yaml()
    data = yaml.load(source)
    if data is None:
        return {}
    matrices: dict[str, int] = {}
    errors: list[str] = []
    _walk_matrices(data, '', matrices, errors)
    if errors:
        raise ValueError('Irregular matrix sequences:\n' + '\n'.join(f'  {e}' for e in errors))
    return matrices


# ---------------------------------------------------------------------------
# Post-pass: apply matrix formatting to the yamlfix output
# ---------------------------------------------------------------------------


def _parse_path(path: str) -> list[str | int]:
    """Split a YAML path like 'a.b[0].c' into navigation keys/indices."""
    parts: list[str | int] = []
    # Split on dots that are not inside brackets
    for segment in re.split(r'\.(?![^\[]*\])', path):
        m = re.fullmatch(r'([^\[]+)(?:\[(\d+)\])?', segment)
        if m:
            parts.append(m.group(1))
            if m.group(2) is not None:
                parts.append(int(m.group(2)))
    return parts


def _navigate(data: Any, parts: list[str | int]) -> Any:
    node = data
    for part in parts:
        node = node[part]
    return node


def _build_line_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _find_bracket_span(source: str, search_from: int) -> tuple[int, int] | None:
    """Find the (start, end) char span of a top-level [...] searching forward."""
    bracket_start = source.find('[', search_from)
    if bracket_start == -1:
        return None
    depth = 0
    in_str = False
    str_char = ''
    for i in range(bracket_start, len(source)):
        ch = source[i]
        if in_str:
            if ch == str_char:
                in_str = False
        elif ch in ('"', "'"):
            in_str = True
            str_char = ch
        elif ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return bracket_start, i + 1
    return None


def _parse_flow_items(bracket_text: str) -> list[str]:
    """Extract item strings from a flow sequence like '[a, b, c]'."""
    inner = bracket_text[1:-1]
    items: list[str] = []
    depth = 0
    current: list[str] = []
    in_str = False
    str_char = ''
    for ch in inner:
        if in_str:
            current.append(ch)
            if ch == str_char:
                in_str = False
        elif ch in ('"', "'"):
            in_str = True
            str_char = ch
            current.append(ch)
        elif ch in '[{(':
            depth += 1
            current.append(ch)
        elif ch in ']})':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            item = ''.join(current).strip()
            if item:
                items.append(item)
            current = []
        else:
            current.append(ch)
    item = ''.join(current).strip()
    if item:
        items.append(item)
    return items


def _format_matrix(items: list[str], items_per_row: int, bracket_col: int) -> str:
    """Render items as an N-per-row, column-aligned flow sequence string.

    bracket_col is the column position of '[' in the output, used to compute
    the indentation of continuation lines.

    Each field (item + comma) is padded to a uniform width per column so that
    values in the same column align across rows, with the space appearing after
    the comma rather than before it:

        [1e-4, 0.0,  0.0,
         0.0,  1e-4, 0.0,
         0.0,  0.0,  1e-4]
    """
    rows = [items[i : i + items_per_row] for i in range(0, len(items), items_per_row)]
    num_cols = items_per_row
    col_widths = [0] * num_cols
    for row in rows:
        for j, item in enumerate(row):
            if j < num_cols:
                col_widths[j] = max(col_widths[j], len(item))
    # Continuation lines align with the first character after '['
    indent = ' ' * (bracket_col + 1)
    formatted_rows: list[str] = []
    for ri, row in enumerate(rows):
        is_last_row = ri == len(rows) - 1
        row_str = ''
        for j, item in enumerate(row):
            is_last_item = is_last_row and j == len(row) - 1
            is_last_in_row = j == len(row) - 1
            if is_last_item:
                row_str += item
            elif is_last_in_row:
                # Last item of a non-last row: comma but no trailing pad
                row_str += item + ','
            else:
                # Non-terminal: pad the "item," field to col_width + 2 so the
                # next column starts at a consistent position across rows
                row_str += (item + ',').ljust(col_widths[j] + 2)
        formatted_rows.append(row_str)
    return '[' + ('\n' + indent).join(formatted_rows) + ']'


def apply_matrices(source: str, matrices: dict[str, int]) -> str:
    """Replace flat flow sequences in source with their matrix-formatted versions."""
    if not matrices:
        return source
    yaml = _make_yaml()
    data = yaml.load(source)
    if data is None:
        return source

    line_offsets = _build_line_offsets(source)
    replacements: list[tuple[int, int, str]] = []

    for path, items_per_row in matrices.items():
        parts = _parse_path(path)
        try:
            parent = _navigate(data, parts[:-1])
            key = parts[-1]
        except (KeyError, IndexError, TypeError):
            continue
        if not isinstance(parent, CommentedMap):
            continue
        lc_entry = parent.lc.data.get(key)
        if lc_entry is None:
            continue
        val_line, val_col = lc_entry[2], lc_entry[3]
        search_from = line_offsets[val_line] + val_col
        span = _find_bracket_span(source, search_from)
        if span is None:
            continue
        bracket_start, bracket_end = span
        items = _parse_flow_items(source[bracket_start:bracket_end])
        line_start = source.rfind('\n', 0, bracket_start) + 1
        bracket_col = bracket_start - line_start
        replacements.append((bracket_start, bracket_end, _format_matrix(items, items_per_row, bracket_col)))

    # Apply in reverse order so earlier character positions remain valid
    for start, end, replacement in sorted(replacements, key=lambda r: r[0], reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def format_yaml(source: str) -> str:
    """Format YAML source, preserving matrix-structured flow sequences.

    Raises ValueError for irregular multi-line flow sequences.
    """
    matrices = detect_matrices(source)
    fixed = fix_code(source, _yamlfix_config())
    if matrices:
        fixed = apply_matrices(fixed, matrices)
    return fixed


def format_yaml_files(files: list[str]) -> list[tuple[str, bool, str]]:
    """Format YAML files in place.

    Returns [(filepath, was_changed, error_message)] for each file.
    error_message is non-empty only on failure; was_changed is False on failure.
    """
    results = []
    for filepath in files:
        path = Path(filepath)
        try:
            original = path.read_text(encoding='utf-8')
            formatted = format_yaml(original)
        except ValueError as exc:
            results.append((filepath, False, str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001
            results.append((filepath, False, f'Error: {exc}'))
            continue
        changed = formatted != original
        if changed:
            path.write_text(formatted, encoding='utf-8')
        results.append((filepath, changed, ''))
    return results
