# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse
import functools

from lxml import etree

from polymath_code_standard.checker import CONFIG_DIR, CheckerGroup, Result, check_group

# Schemas bundled as package resources; any other URL is fetched from the network.
_BUNDLED_SCHEMAS: dict[str, str] = {
    'http://download.ros.org/schema/package_format3.xsd': CONFIG_DIR / 'package_format3.xsd',
}


@functools.cache
def _load_schema(url: str) -> etree.XMLSchema:
    src = _BUNDLED_SCHEMAS.get(url, url)
    return etree.XMLSchema(etree.parse(src))


def _schema_urls(doc: etree._ElementTree) -> list[str]:
    """Return XSD schema URLs referenced by the document."""
    urls = []
    node = doc.getroot().getprevious()
    while node is not None:
        if isinstance(node, etree._ProcessingInstruction) and node.target == 'xml-model':
            pi = etree.fromstring(f'<pi {node.text}/>')
            href = pi.get('href')
            if href and pi.get('schematypens') == 'http://www.w3.org/2001/XMLSchema':
                urls.append(href)
        node = node.getprevious()
    xsi = 'http://www.w3.org/2001/XMLSchema-instance'
    loc = doc.getroot().get(f'{{{xsi}}}noNamespaceSchemaLocation')
    if loc:
        urls.append(loc)
    return urls


def _validate_xml(filepath: str) -> list[str]:
    """Well-formedness + schema validation. Returns error strings."""
    try:
        doc = etree.parse(filepath)
    except etree.XMLSyntaxError as exc:
        return [str(e) for e in exc.error_log]
    errors = []
    for url in _schema_urls(doc):
        try:
            schema = _load_schema(url)
        except Exception as exc:
            errors.append(f'failed to load schema {url}: {exc}')
            continue
        if not schema.validate(doc):
            errors.extend(str(e) for e in schema.error_log)
    return errors


@check_group
class XmlGroup(CheckerGroup):
    name = 'xml'

    def run(self, args: argparse.Namespace) -> list[Result]:
        if not args.files:
            return [Result(name='xml-validate', passed=True, skipped=True)]

        all_errors = []
        for f in args.files:
            for msg in _validate_xml(f):
                all_errors.append(f'{f}: {msg}')
        return [
            Result(
                name='xml-validate',
                passed=not all_errors,
                output='\n'.join(all_errors),
            )
        ]
