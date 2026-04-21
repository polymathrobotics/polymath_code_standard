# Copyright (c) 2026-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""Tests for the YAML formatter with matrix-preserving flow sequence support."""

import textwrap

import pytest

from polymath_code_standard.yaml_format import detect_matrices, format_yaml

# ---------------------------------------------------------------------------
# detect_matrices
# ---------------------------------------------------------------------------


class TestDetectMatrices:
    def test_single_line_sequence_ignored(self):
        source = 'tags: [a, b, c]\n'
        assert detect_matrices(source) == {}

    def test_single_item_sequence_ignored(self):
        source = 'items: [42]\n'
        assert detect_matrices(source) == {}

    def test_empty_document(self):
        assert detect_matrices('') == {}

    def test_3x3_matrix_detected(self):
        source = textwrap.dedent("""\
            covariance: [1e-4, 0.0,  0.0,
                         0.0,  1e-4, 0.0,
                         0.0,  0.0,  1e-4]
        """)
        assert detect_matrices(source) == {'covariance': 3}

    def test_6_wide_matrix_detected(self):
        source = textwrap.dedent("""\
            process_noise_covariance: [1e-9, 0.0,  0.0,  0.0,  0.0,  0.0,
                                       0.0,  1e-9, 0.0,  0.0,  0.0,  0.0,
                                       0.0,  0.0,  1e-3, 0.0,  0.0,  0.0,
                                       0.0,  0.0,  0.0,  1e-3, 0.0,  0.0,
                                       0.0,  0.0,  0.0,  0.0,  1e-9, 0.0,
                                       0.0,  0.0,  0.0,  0.0,  0.0,  1e-9]
        """)
        assert detect_matrices(source) == {'process_noise_covariance': 6}

    def test_partial_last_row_is_ok(self):
        # 7 items in a 3-per-row layout: rows [3, 3, 1]
        source = textwrap.dedent("""\
            items: [1, 2, 3,
                    4, 5, 6,
                    7]
        """)
        assert detect_matrices(source) == {'items': 3}

    def test_nested_key(self):
        source = textwrap.dedent("""\
            robot:
              covariance: [1.0, 0.0,
                           0.0, 1.0]
        """)
        assert detect_matrices(source) == {'robot.covariance': 2}

    def test_irregular_middle_row_raises(self):
        # Row sizes [2, 3, 1] — middle row has more items than first
        source = textwrap.dedent("""\
            bad: [1, 2,
                  3, 4, 5,
                  6]
        """)
        with pytest.raises(ValueError, match='Irregular matrix'):
            detect_matrices(source)

    def test_last_row_exceeds_first_raises(self):
        # Row sizes [2, 3] — last row has more items than first
        source = textwrap.dedent("""\
            bad: [1, 2,
                  3, 4, 5]
        """)
        with pytest.raises(ValueError, match='Irregular matrix'):
            detect_matrices(source)

    def test_multiple_matrices_detected(self):
        source = textwrap.dedent("""\
            a: [1, 2,
                3, 4]
            b: [x, y, z,
                p, q, r]
        """)
        assert detect_matrices(source) == {'a': 2, 'b': 3}


# ---------------------------------------------------------------------------
# format_yaml — yamlfix normalisation
# ---------------------------------------------------------------------------


class TestFormatYamlNormalisation:
    def test_empty_file(self):
        result = format_yaml('')
        assert result == ''

    def test_adds_document_start(self):
        result = format_yaml('key: value\n')
        assert result.startswith('---\n')

    def test_true_normalised(self):
        result = format_yaml('enabled: True\n')
        assert 'enabled: true' in result

    def test_false_normalised(self):
        result = format_yaml('enabled: False\n')
        assert 'enabled: false' in result

    def test_single_line_sequence_preserved(self):
        result = format_yaml('tags: [a, b, c]\n')
        assert '[a, b, c]' in result


# ---------------------------------------------------------------------------
# format_yaml — matrix preservation
# ---------------------------------------------------------------------------


class TestFormatYamlMatrix:
    def test_3x3_matrix_preserved(self):
        source = textwrap.dedent("""\
            covariance: [1e-4, 0.0,  0.0,
                         0.0,  1e-4, 0.0,
                         0.0,  0.0,  1e-4]
        """)
        result = format_yaml(source)
        assert result == textwrap.dedent("""\
            ---
            covariance: [1e-4, 0.0,  0.0,
                         0.0,  1e-4, 0.0,
                         0.0,  0.0,  1e-4]
        """)

    def test_column_alignment(self):
        source = textwrap.dedent("""\
            cov: [1e-4, 0.0,
                  0.0,  1e-4]
        """)
        result = format_yaml(source)
        assert result == textwrap.dedent("""\
            ---
            cov: [1e-4, 0.0,
                  0.0,  1e-4]
        """)

    def test_boolean_matrix_normalised_and_preserved(self):
        source = textwrap.dedent("""\
            odom0_config: [False, True, False,
                           True, False, False]
        """)
        result = format_yaml(source)
        assert result == textwrap.dedent("""\
            ---
            odom0_config: [false, true,  false,
                           true,  false, false]
        """)

    def test_irregular_matrix_raises(self):
        source = textwrap.dedent("""\
            bad: [1, 2,
                  3, 4, 5]
        """)
        with pytest.raises(ValueError, match='Irregular matrix'):
            format_yaml(source)

    def test_6x6_matrix_shape(self):
        source = textwrap.dedent("""\
            process_noise_covariance: [1e-9, 0.0, 0.0, 0.0, 0.0, 0.0,
                                       0.0, 1e-9, 0.0, 0.0, 0.0, 0.0,
                                       0.0, 0.0, 1e-3, 0.0, 0.0, 0.0,
                                       0.0, 0.0, 0.0, 1e-3, 0.0, 0.0,
                                       0.0, 0.0, 0.0, 0.0, 1e-9, 0.0,
                                       0.0, 0.0, 0.0, 0.0, 0.0, 1e-9]
        """)
        result = format_yaml(source)
        assert result == textwrap.dedent("""\
            ---
            process_noise_covariance: [1e-9, 0.0,  0.0,  0.0,  0.0,  0.0,
                                       0.0,  1e-9, 0.0,  0.0,  0.0,  0.0,
                                       0.0,  0.0,  1e-3, 0.0,  0.0,  0.0,
                                       0.0,  0.0,  0.0,  1e-3, 0.0,  0.0,
                                       0.0,  0.0,  0.0,  0.0,  1e-9, 0.0,
                                       0.0,  0.0,  0.0,  0.0,  0.0,  1e-9]
        """)

    def test_idempotent_single_line(self):
        source = '---\ntags: [a, b, c]\n'
        assert format_yaml(source) == format_yaml(format_yaml(source))

    def test_idempotent_matrix(self):
        source = textwrap.dedent("""\
            covariance: [1e-4, 0.0,  0.0,
                         0.0,  1e-4, 0.0,
                         0.0,  0.0,  1e-4]
        """)
        first = format_yaml(source)
        second = format_yaml(first)
        assert first == second

    def test_mixed_sequences_in_same_file(self):
        source = textwrap.dedent("""\
            tags: [a, b, c]
            covariance: [1.0,  0.0,
                        0.0, 1.0]
        """)
        result = format_yaml(source)
        assert result == textwrap.dedent("""\
            ---
            tags: [a, b, c]
            covariance: [1.0, 0.0,
                         0.0, 1.0]
        """)
