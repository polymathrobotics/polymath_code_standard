# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the executor thread-count linter."""

import pytest

from polymath_code_standard.checkers.ros.executor_lint import check_executor_threads, find_violations

# Constructions that MUST be flagged (no explicit, non-zero thread count).
FLAGGED = [
    'rclcpp::executors::MultiThreadedExecutor executor;',
    'rclcpp::executors::EventsCBGExecutor exec;',
    'MultiThreadedExecutor executor;',
    'auto e = rclcpp::executors::MultiThreadedExecutor();',
    'rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions());',
    'auto e = std::make_shared<rclcpp::executors::MultiThreadedExecutor>();',
    'auto e = new rclcpp::executors::EventsCBGExecutor();',
    'rclcpp::executors::MultiThreadedExecutor executor{};',
]

# Constructions and references that MUST NOT be flagged.
CLEAN = [
    'rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(), 4);',
    'MultiThreadedExecutor executor(rclcpp::ExecutorOptions(), 0);',
    'rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(), node->getNumThreads());',
    'auto e = std::make_shared<rclcpp::executors::EventsCBGExecutor>(rclcpp::ExecutorOptions(), 2);',
    'rclcpp::executors::SingleThreadedExecutor executor;',
    'void f(rclcpp::executors::MultiThreadedExecutor & exec);',
    'using Exec = rclcpp::executors::MultiThreadedExecutor;',
    'typedef rclcpp::executors::MultiThreadedExecutor Exec;',
    '// rclcpp::executors::MultiThreadedExecutor executor;',
    'const char * s = "MultiThreadedExecutor executor;";',
    'rclcpp::executors::MultiThreadedExecutor executor;  // NOLINT(custom)',
]


@pytest.mark.parametrize('src', FLAGGED)
def test_flagged(src):
    assert find_violations(src), f'expected a violation for: {src}'


@pytest.mark.parametrize('src', CLEAN)
def test_clean(src):
    # NOLINT suppression is applied at the file level, so route through check_*.
    assert not find_violations(src) or 'NOLINT' in src, f'unexpected violation for: {src}'


def test_nolint_suppresses(tmp_path):
    f = tmp_path / 'a.cpp'
    f.write_text('rclcpp::executors::MultiThreadedExecutor executor;  // NOLINT\n')
    assert check_executor_threads([str(f)]).passed


def test_check_reports_path_and_line(tmp_path):
    f = tmp_path / 'b.cpp'
    f.write_text('int main() {\n  rclcpp::executors::MultiThreadedExecutor exec;\n}\n')
    result = check_executor_threads([str(f)])
    assert not result.passed
    assert f'{f}:2:' in result.output


def test_multiline_ctor_with_threads_is_clean(tmp_path):
    f = tmp_path / 'c.cpp'
    f.write_text('rclcpp::executors::MultiThreadedExecutor exec(\n    rclcpp::ExecutorOptions(),\n    4);\n')
    assert check_executor_threads([str(f)]).passed


def test_empty_file_list_skipped():
    assert check_executor_threads([]).skipped
