# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
import argparse

from polymath_code_standard.checker import CheckerGroup, Result, check_group
from polymath_code_standard.yaml_format import format_yaml_files


@check_group
class YamlGroup(CheckerGroup):
    name = 'yaml'

    def run(self, args: argparse.Namespace) -> list[Result]:
        if not args.files:
            return [Result(name='yamlfix', passed=True, skipped=True)]
        errors, changed = [], []
        for filepath, was_changed, error in format_yaml_files(args.files):
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
