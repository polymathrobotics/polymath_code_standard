# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
import argparse

from polymath_code_standard.checker import CheckerGroup, Result, check_group
from polymath_code_standard.yaml_format import format_yaml_files


@check_group
class YamlGroup(CheckerGroup):
    name = 'yaml'

    def register_args(self, subparser: argparse.ArgumentParser) -> None:
        super().register_args(subparser)
        subparser.add_argument(
            '--no-explicit-start',
            action='store_true',
            help='Do not add --- header to YAML files',
        )

    def run(self, args: argparse.Namespace) -> list[Result]:
        if not args.files:
            return [Result(name='yamlfix', passed=True, skipped=True)]
        errors, changed = [], []
        explicit_start = not args.no_explicit_start
        for filepath, was_changed, error in format_yaml_files(args.files, explicit_start=explicit_start):
            if error:
                errors.append(f'{filepath}: {error}')
            elif was_changed:
                changed.append(filepath)
        results = []
        if errors:
            results.append(Result(name='yamlfix', passed=False, output='\n'.join(errors)))
        if changed:
            changed_list = '\n'.join(f'  {f}' for f in changed)
            results.append(
                Result(
                    name='yamlfix',
                    passed=False,
                    output=f'Files reformatted — please re-stage and recommit:\n{changed_list}',
                )
            )
        if not results:
            results.append(Result(name='yamlfix', passed=True))
        return results
