# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Require an explicit thread count for multi-threaded rclcpp executors.

A default-constructed MultiThreadedExecutor / EventsCBGExecutor spawns
``hardware_concurrency()`` threads (one per core).
Their constructors take ``number_of_threads`` as the 2nd
positional arg, so a bounded count needs ``Type(rclcpp::ExecutorOptions(), N)``;
``0`` defaults to std::hardware_concurrency, so is disallowed.

Detection is heuristic (regex + balanced-paren parsing).
To suppress, use a trailing ``// NOLINT``.
"""

import re
from pathlib import Path

from polymath_code_standard.checker import Result

# Executors whose 2nd positional ctor arg is number_of_threads.
THREADED_EXECUTORS = ('MultiThreadedExecutor', 'EventsCBGExecutor')

_TYPE_RE = re.compile(r'(?:[A-Za-z_]\w*::)*(' + '|'.join(THREADED_EXECUTORS) + r')\b')


def _blank(span: str) -> str:
    """Spaces of equal length to ``span``, with newlines left in place."""
    return ''.join('\n' if c == '\n' else ' ' for c in span)


def _string_end(text: str, start: int) -> int:
    """Index just past the string/char literal whose opening quote is at ``start``."""
    quote = text[start]
    i = start + 1
    while i < len(text):
        if text[i] == '\\':  # escape consumes the next char, including a quote
            i += 2
        elif text[i] == quote:
            return i + 1
        else:
            i += 1
    return len(text)


def _blank_comments_and_strings(text: str) -> str:
    """Blank comments and string/char literals to spaces. The result keeps the
    same length and newline positions as ``text``, so offsets and line numbers
    computed on it map straight back to the original."""
    out = []
    i, n = 0, len(text)
    while i < n:
        pair = text[i : i + 2]
        if pair == '//':
            end = text.find('\n', i)
            end = n if end == -1 else end
        elif pair == '/*':
            end = text.find('*/', i + 2)
            end = n if end == -1 else end + 2
        elif text[i] in '"\'':
            end = _string_end(text, i)
        else:
            out.append(text[i])
            i += 1
            continue
        out.append(_blank(text[i:end]))
        i = end
    return ''.join(out)


def _skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def _parse_arg_list(text: str, open_idx: int) -> list[str] | None:
    """Top-level comma-split of the bracketed list starting at ``open_idx``.

    Depth is tracked uniformly across (), [] and {} so nested calls like
    ``ExecutorOptions()`` count as part of one argument. Returns None if the
    list is unbalanced (parse gave up — caller should not flag)."""
    depth = 0
    args: list[str] = []
    buf: list[str] = []
    for c in text[open_idx:]:
        if c in '([{':
            depth += 1
            if depth == 1:
                continue
            buf.append(c)
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                tail = ''.join(buf).strip()
                if args or tail:
                    args.append(tail)
                return args
            buf.append(c)
        elif c == ',' and depth == 1:
            args.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(c)
    return None


def find_violations(text: str) -> list[tuple[int, str]]:
    """Return (1-based line, type name) for each unbounded executor construction."""
    code = _blank_comments_and_strings(text)
    violations = []
    for m in _TYPE_RE.finditer(code):
        type_name = m.group(1)

        # Skip type aliases — ``typedef X Y;`` / ``using Y = X;`` are not ctors.
        stmt_start = (
            max(
                code.rfind(';', 0, m.start()),
                code.rfind('{', 0, m.start()),
                code.rfind('}', 0, m.start()),
            )
            + 1
        )
        if re.search(r'\b(?:typedef|using)\b', code[stmt_start : m.start()]):
            continue

        j = _skip_ws(code, m.end())
        if j >= len(code):
            continue
        ch = code[j]
        args: list[str] | None = None
        default_ctor = False

        if ch in '({':  # Type(...) / Type{...} temporary or direct init
            args = _parse_arg_list(code, j)
        elif ch == '_' or ch.isalpha():  # Type varname ...
            k = j
            while k < len(code) and (code[k].isalnum() or code[k] == '_'):
                k += 1
            k = _skip_ws(code, k)
            if k < len(code) and code[k] in '({':
                args = _parse_arg_list(code, k)
            elif k < len(code) and code[k] in ';,)=':
                default_ctor = True  # Type var;  (no initializer)
            else:
                continue
        elif ch == '>':  # make_shared<...Type>( ... )
            k = _skip_ws(code, j + 1)
            if k < len(code) and code[k] == '(':
                args = _parse_arg_list(code, k)
            else:
                continue
        else:
            continue  # reference / pointer / unrelated token

        if default_ctor:
            bounded = False
        elif args is None:
            continue  # unbalanced — don't risk a false positive
        else:
            bounded = len(args) >= 2 and args[1] not in ('', '0')
        if not default_ctor and bounded:
            continue

        line = code.count('\n', 0, m.start()) + 1
        violations.append((line, type_name))
    return violations


def check_executor_threads(cpp_files: list[str]) -> Result:
    name = 'executor-threads'
    if not cpp_files:
        return Result(name=name, passed=True, skipped=True)
    findings = []
    for path in cpp_files:
        try:
            text = Path(path).read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        src_lines = text.splitlines()
        for lineno, type_name in find_violations(text):
            if 0 <= lineno - 1 < len(src_lines) and 'NOLINT' in src_lines[lineno - 1]:
                continue
            findings.append(
                f'{path}:{lineno}: {type_name} constructed without an explicit thread count; '
                f'pass number_of_threads, e.g. {type_name}(rclcpp::ExecutorOptions(), N) '
                f'(use // NOLINT to suppress) [executor-threads]'
            )
    if findings:
        return Result(name=name, passed=False, output='\n'.join(findings))
    return Result(name=name, passed=True)
