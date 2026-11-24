# SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the package.xml dependency formatter."""

import argparse
import textwrap

import pytest

from polymath_code_standard.checkers.xml import XmlGroup
from polymath_code_standard.package_xml_format import format_package_xml

HEAD = """\
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>pkg</name>
  <version>0.0.0</version>
  <description>Test</description>
  <maintainer email="a@b.com">A</maintainer>
  <license>Apache-2.0</license>

"""
TAIL = """
  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
"""


def package(depends: str) -> str:
    return HEAD + textwrap.indent(textwrap.dedent(depends), '  ', lambda line: line.strip() != '') + TAIL


def assert_formats(before: str, after: str) -> None:
    assert format_package_xml(package(before)) == package(after)
    assert format_package_xml(package(after)) == package(after)


def test_groups_in_lifecycle_order_and_sorts():
    assert_formats(
        """\
        <test_depend>b_test</test_depend>
        <depend>rclcpp</depend>
        <doc_depend>docs</doc_depend>
        <exec_depend>b_exec</exec_depend>
        <test_depend>a_test</test_depend>
        <build_export_depend>bed</build_export_depend>
        <depend>eigen</depend>
        <build_depend>bd</build_depend>
        <buildtool_export_depend>bted</buildtool_export_depend>
        <exec_depend>a_exec</exec_depend>
        <buildtool_depend>ament_cmake</buildtool_depend>
        """,
        """\
        <buildtool_depend>ament_cmake</buildtool_depend>

        <buildtool_export_depend>bted</buildtool_export_depend>

        <build_depend>bd</build_depend>

        <build_export_depend>bed</build_export_depend>

        <depend>eigen</depend>
        <depend>rclcpp</depend>

        <exec_depend>a_exec</exec_depend>
        <exec_depend>b_exec</exec_depend>

        <test_depend>a_test</test_depend>
        <test_depend>b_test</test_depend>

        <doc_depend>docs</doc_depend>
        """,
    )


def test_merges_blocks_and_normalizes_blank_lines():
    assert_formats(
        """\
        <depend>b</depend>


        <depend>a</depend>

        <depend>c</depend>
        """,
        """\
        <depend>a</depend>
        <depend>b</depend>
        <depend>c</depend>
        """,
    )


def test_condition_breaks_ties_and_attributes_are_kept():
    assert_formats(
        """\
        <depend condition="$ROS_DISTRO == jazzy">gz_vendor</depend>
        <depend version_gte="1.0">abc</depend>
        <depend condition="$ROS_DISTRO == humble">gz_vendor</depend>
        """,
        """\
        <depend version_gte="1.0">abc</depend>
        <depend condition="$ROS_DISTRO == humble">gz_vendor</depend>
        <depend condition="$ROS_DISTRO == jazzy">gz_vendor</depend>
        """,
    )


def test_comment_heads_a_section_after_the_uncommented_block():
    assert_formats(
        """\
        <!-- Launched directly -->
        <exec_depend>z_launch</exec_depend>
        <exec_depend>y_launch</exec_depend>

        <exec_depend>b</exec_depend>
        <depend>rclcpp</depend>
        <exec_depend>a</exec_depend>
        <!-- Developer tools -->
        <exec_depend>tool</exec_depend>
        """,
        """\
        <depend>rclcpp</depend>

        <exec_depend>a</exec_depend>
        <exec_depend>b</exec_depend>

        <!-- Launched directly -->
        <exec_depend>y_launch</exec_depend>
        <exec_depend>z_launch</exec_depend>

        <!-- Developer tools -->
        <exec_depend>tool</exec_depend>
        """,
    )


def test_multiline_and_stacked_comments_stay_together():
    assert_formats(
        """\
        <!-- First line
             second line -->
        <!-- Another note -->
        <exec_depend>b</exec_depend>
        <exec_depend>a</exec_depend>
        """,
        """\
        <!-- First line
             second line -->
        <!-- Another note -->
        <exec_depend>a</exec_depend>
        <exec_depend>b</exec_depend>
        """,
    )


def test_trailing_comment_moves_with_its_dependency():
    assert_formats(
        """\
        <depend>b</depend> <!-- why b -->
        <depend>a</depend>
        """,
        """\
        <depend>a</depend>
        <depend>b</depend> <!-- why b -->
        """,
    )


def test_commented_out_dependency_sorts_as_a_dependency():
    assert_formats(
        """\
        <depend>c</depend>
        <!-- <depend>b</depend> -->
        <depend>a</depend>
        """,
        """\
        <depend>a</depend>
        <!-- <depend>b</depend> -->
        <depend>c</depend>
        """,
    )


def test_comment_after_dependencies_is_left_alone():
    source = package(
        """\
        <depend>a</depend>

        <!-- Export for pluginlib -->
        """
    )
    assert format_package_xml(source) == source


def test_reindents_to_first_dependency():
    assert_formats(
        """\
        <depend>b</depend>
            <depend>a</depend>
        """,
        """\
        <depend>a</depend>
        <depend>b</depend>
        """,
    )


def test_section_with_several_kinds_fails():
    source = package(
        """\
        <!-- Mixed -->
        <depend>a</depend>
        <exec_depend>b</exec_depend>
        """
    )
    with pytest.raises(ValueError, match='several kinds'):
        format_package_xml(source)


def test_comment_without_dependency_fails():
    source = package(
        """\
        <depend>a</depend>
        <!-- Orphan -->

        <exec_depend>b</exec_depend>
        """
    )
    with pytest.raises(ValueError, match='not followed by a dependency'):
        format_package_xml(source)


def test_dependencies_sharing_a_line_fail():
    source = package('<depend>b</depend><depend>a</depend>\n')
    with pytest.raises(ValueError, match='own line'):
        format_package_xml(source)


@pytest.mark.parametrize(
    'source',
    [
        '<package format="1"><name>x</name><run_depend>b</run_depend><build_depend>a</build_depend></package>\n',
        '<launch><depend>b</depend><depend>a</depend></launch>\n',
        package(''),
    ],
)
def test_unchanged(source):
    assert format_package_xml(source) == source


def test_xml_group_reformats_package_xml(tmp_path):
    path = tmp_path / 'package.xml'
    path.write_text(package('<depend>b</depend>\n<depend>a</depend>\n'))
    other = tmp_path / 'other.xml'
    other.write_text(package('<depend>b</depend>\n<depend>a</depend>\n'))
    results = XmlGroup().run(argparse.Namespace(files=[str(path), str(other)]))
    formatted = next(r for r in results if r.name == 'package-xml-format')
    assert not formatted.passed
    assert str(path) in formatted.output
    assert path.read_text() == package('<depend>a</depend>\n<depend>b</depend>\n')
    assert other.read_text() == package('<depend>b</depend>\n<depend>a</depend>\n')
