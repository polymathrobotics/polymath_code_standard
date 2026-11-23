# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Formatter for the dependency list of a ROS package.xml.

Dependencies are grouped into blank-line separated blocks, one per tag, in DEPEND_ORDER.
Each block is sorted by package name.

A comment between dependencies heads a section.
The section holds the dependencies that follow the comment, up to the next blank line or comment.
It stays together, sorted, after the uncommented block of its tag.
All dependencies in a section must share one tag.

A comment that holds a single dependency element, such as a commented-out dependency,
sorts as that dependency.

Everything outside the dependency list is left untouched.
Files whose root is not a format 2 or 3 <package> are returned unchanged.

Raises ValueError if the dependency list cannot be rewritten line by line,
for example when a dependency shares a line with another element.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

DEPEND_ORDER = (
    'buildtool_depend',
    'buildtool_export_depend',
    'build_depend',
    'build_export_depend',
    'depend',
    'exec_depend',
    'test_depend',
    'doc_depend',
)

_COMMENTED_DEPEND = re.compile(
    r'\s*<(?P<tag>' + '|'.join(DEPEND_ORDER) + r')\b(?P<attrs>[^>]*)>\s*(?P<name>[^<\s]+)\s*</(?P=tag)>\s*',
)
_CONDITION = re.compile(r'\bcondition\s*=\s*(["\'])(.*?)\1')


@dataclass
class _Depend:
    tag: str
    name: str
    condition: str
    lines: list[str]

    def sort_key(self) -> tuple[str, str, str]:
        return (self.name, self.condition, '\n'.join(self.lines))


@dataclass
class _Section:
    comment: list[str]
    depends: list[_Depend] = field(default_factory=list)


@dataclass
class _Unit:
    """One or more whole source lines holding a dependency, a comment, or a dependency with a trailing comment."""

    first: int
    last: int
    node: etree._Element
    tail: str


def _span(node: etree._Element) -> tuple[int, int]:
    """Return the 0-based first and last source line of a direct child of the root."""
    text = node.text or ''
    if isinstance(node, etree._Comment):
        # libxml2 records the line a comment ends on.
        return node.sourceline - 1 - text.count('\n'), node.sourceline - 1
    if '\n' in text or len(node):
        raise ValueError(f'line {node.sourceline}: <{node.tag}> must fit on one line')
    return node.sourceline - 1, node.sourceline - 1


def _is_depend(node: etree._Element) -> bool:
    return not isinstance(node, etree._Comment) and node.tag in DEPEND_ORDER


def _depend_region(root: etree._Element) -> list[etree._Element]:
    """Return the root children from the comments before the first dependency through the last dependency."""
    children = list(root)
    indices = [i for i, child in enumerate(children) if _is_depend(child)]
    if not indices:
        return []
    start, end = indices[0], indices[-1]
    while start > 0 and isinstance(children[start - 1], etree._Comment):
        start -= 1
    # A comment on the line where the preceding element ends belongs to that element.
    while start < indices[0] and '\n' not in _preceding_text(root, children, start):
        start += 1
    region = children[start : end + 1]
    for node in region:
        if not isinstance(node, etree._Comment) and not _is_depend(node):
            raise ValueError(f'line {node.sourceline}: <{node.tag}> sits between dependencies')
    # A comment trailing the last dependency on its line belongs to it.
    while (
        end + 1 < len(children)
        and isinstance(children[end + 1], etree._Comment)
        and '\n' not in (children[end].tail or '')
    ):
        end += 1
        region.append(children[end])
    return region


def _preceding_text(root: etree._Element, children: list[etree._Element], index: int) -> str:
    return (children[index - 1].tail if index else root.text) or ''


def _units(root: etree._Element, region: list[etree._Element]) -> list[_Unit]:
    children = list(root)
    first_index = children.index(region[0])
    if '\n' not in _preceding_text(root, children, first_index):
        raise ValueError(f'line {region[0].sourceline}: the first dependency must start its own line')
    units: list[_Unit] = []
    for node in region:
        first, last = _span(node)
        prev = units[-1] if units else None
        if prev is not None and '\n' not in prev.tail:
            if not isinstance(node, etree._Comment):
                raise ValueError(f'line {node.sourceline}: each dependency must be on its own line')
            prev.last = last
            prev.tail = node.tail or ''
            continue
        units.append(_Unit(first, last, node, node.tail or ''))
    if '\n' not in units[-1].tail:
        raise ValueError(f'line {region[-1].sourceline}: the last dependency must end its line')
    return units


def _commented_depend(node: etree._Element, lines: list[str]) -> _Depend | None:
    if not isinstance(node, etree._Comment):
        return None
    match = _COMMENTED_DEPEND.fullmatch(node.text or '')
    if match is None:
        return None
    condition = _CONDITION.search(match['attrs'])
    return _Depend(match['tag'], match['name'], condition[2] if condition else '', lines)


def _parse(units: list[_Unit], lines: list[str]) -> tuple[dict[str, list[_Depend]], list[_Section]]:
    loose: dict[str, list[_Depend]] = {tag: [] for tag in DEPEND_ORDER}
    sections: list[_Section] = []
    section: _Section | None = None
    prev_last: int | None = None
    for unit in units:
        unit_lines = lines[unit.first : unit.last + 1]
        if section is not None and prev_last is not None and unit.first > prev_last + 1:
            section = None
        prev_last = unit.last
        depend = _commented_depend(unit.node, unit_lines)
        if depend is None and isinstance(unit.node, etree._Comment):
            if section is not None and not section.depends:
                section.comment.extend(unit_lines)
            else:
                section = _Section(unit_lines)
                sections.append(section)
            continue
        if depend is None:
            depend = _Depend(unit.node.tag, (unit.node.text or '').strip(), unit.node.get('condition', ''), unit_lines)
        if section is None:
            loose[depend.tag].append(depend)
        else:
            section.depends.append(depend)
    for section in sections:
        if not section.depends:
            raise ValueError(f'comment "{section.comment[0].strip()}" is not followed by a dependency')
        tags = sorted({depend.tag for depend in section.depends}, key=DEPEND_ORDER.index)
        if len(tags) > 1:
            raise ValueError(
                f'comment "{section.comment[0].strip()}" heads dependencies of several kinds ({", ".join(tags)}),'
                ' separate them with a blank line'
            )
    return loose, sections


def _reindent(block: list[str], indent: str) -> list[str]:
    return [indent + block[0].lstrip()] + block[1:]


def _sorted_lines(depends: list[_Depend], indent: str) -> list[str]:
    return [line for depend in sorted(depends, key=_Depend.sort_key) for line in _reindent(depend.lines, indent)]


def _render(loose: dict[str, list[_Depend]], sections: list[_Section], indent: str) -> list[str]:
    blocks: list[list[str]] = []
    for tag in DEPEND_ORDER:
        if loose[tag]:
            blocks.append(_sorted_lines(loose[tag], indent))
        for section in sections:
            if section.depends[0].tag != tag:
                continue
            blocks.append(_reindent(section.comment, indent) + _sorted_lines(section.depends, indent))
    out: list[str] = []
    for block in blocks:
        if out:
            out.append('')
        out.extend(block)
    return out


def format_package_xml(source: str) -> str:
    """Return source with its dependency list grouped and sorted.

    Raises ValueError if the source is not well-formed XML or its dependency list cannot be rewritten.
    """
    try:
        root = etree.fromstring(source.encode('utf-8'))
    except etree.XMLSyntaxError as exc:
        raise ValueError(str(exc)) from exc
    if root.tag != 'package' or root.get('format') not in ('2', '3'):
        return source
    region = _depend_region(root)
    if not region:
        return source
    lines = source.split('\n')
    units = _units(root, region)
    loose, sections = _parse(units, lines)
    first_line = lines[units[0].first]
    indent = first_line[: len(first_line) - len(first_line.lstrip())]
    rendered = _render(loose, sections, indent)
    return '\n'.join(lines[: units[0].first] + rendered + lines[units[-1].last + 1 :])


def format_package_xml_files(files: list[str]) -> list[tuple[str, bool, str]]:
    """Format package.xml files in place.

    Returns [(filepath, was_changed, error_message)] for each file.
    error_message is non-empty only on failure; was_changed is False on failure.
    """
    results = []
    for filepath in files:
        path = Path(filepath)
        try:
            original = path.read_text(encoding='utf-8')
            formatted = format_package_xml(original)
        except ValueError as exc:
            results.append((filepath, False, str(exc)))
            continue
        changed = formatted != original
        if changed:
            path.write_text(formatted, encoding='utf-8')
        results.append((filepath, changed, ''))
    return results
