"""Tests for complex scenarios and edge cases."""

import pytest
from tests.conftest import parse_success, parse_failure


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_complex_module(self, parser):
        """Test complex module definition."""
        code = """
        module complex_module(x, y=10, z) {
            if (x > 0) {
                translate([x, y, z]) {
                    for (i = [0:5]) {
                        rotate([0, 0, i * 30]) cube(1);
                    }
                }
            } else {
                sphere(5);
            }
        }
        """
        parse_success(parser, code)

    def test_complex_function(self, parser):
        """Test complex function definition."""
        code = """
        function complex_func(x, y=10) = 
            x > 0 ? 
                let(a = x * 2, b = y + 1) 
                a + b : 
                x < 0 ? -x : 0;
        """
        parse_success(parser, code)

    def test_nested_structures(self, parser):
        """Test deeply nested structures."""
        code = """
        if (true) {
            if (false) {
                for (i = [0:5]) {
                    if (i % 2 == 0) {
                        let(x = i * 2) {
                            cube(x);
                        }
                    }
                }
            }
        }
        """
        parse_success(parser, code)

    def test_complex_expression(self, parser):
        """Test very complex expression."""
        code = """
        x = (a + b) * (c - d) / (e % f) ^ 2 + 
            sin(angle) * cos(angle) - 
            (vec[0] + vec[1]) * vec[2] +
            obj.member.submember;
        """
        parse_success(parser, code)

    def test_complex_list_comprehension(self, parser):
        """Test complex list comprehension."""
        code = """
        x = [for (i = [0:10]) 
            let(j = i * 2) 
            if (j > 5 && j < 20) 
                [for (k = [0:j]) 
                    if (k % 2 == 0) 
                        each [k, k+1]
                ]
        ];
        """
        parse_success(parser, code)

    def test_module_with_all_features(self, parser):
        """Test module using all major features."""
        code = """
        module all_features(size=10, count=5) {
            assert(size > 0, "Size must be positive");
            echo("Creating", count, "objects");
            
            let(step = size / count) {
                for (i = [0:count-1]) {
                    translate([i * step, 0, 0]) {
                        if (i % 2 == 0) {
                            cube(step);
                        } else {
                            sphere(step / 2);
                        }
                    }
                }
            }
        }
        """
        parse_success(parser, code)

    def test_function_with_all_features(self, parser):
        """Test function using all major features."""
        code = """
        function all_features(x, y=10) = 
            assert(x > 0, "x must be positive")
            let(a = x * 2, b = y + 1) 
            a > b ? 
                [for (i = [0:a]) 
                    if (i % 2 == 0) 
                        let(j = i * 2) 
                        j + sin(j)
                ] :
                [a, b, a + b];
        """
        parse_success(parser, code)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimal_code(self, parser):
        """Test minimal valid code."""
        code = ";"
        parse_success(parser, code)

    def test_only_comments(self, parser):
        """Test file with only comments."""
        code = "// Just a comment\n/* Another comment */"
        parse_success(parser, code)

    def test_only_use_include(self, parser):
        """Test file with only use/include statements."""
        code = "use <file1.scad>\ninclude <file2.scad>"
        parse_success(parser, code)

    def test_very_long_expression(self, parser):
        """Test very long expression."""
        code = "x = 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 + 9 + 10;"
        parse_success(parser, code)

    def test_deeply_nested_parentheses(self, parser):
        """Test deeply nested parentheses."""
        code = "x = (((((1 + 2) * 3) / 4) - 5) + 6);"
        parse_success(parser, code)

    def test_multiple_operators(self, parser):
        """Test multiple operators in sequence."""
        code = "x = 1 + 2 - 3 * 4 / 5 % 6 ^ 7;"
        parse_success(parser, code)

    def test_empty_blocks(self, parser):
        """Test multiple empty blocks."""
        code = "{{{{}}}}"
        parse_success(parser, code)

    def test_comments_everywhere(self, parser):
        """Test code with comments everywhere."""
        code = """
        // Comment before
        module /* inline comment */ test(/* param comment */ x) {
            // body comment
            cube(/* arg comment */ 10); // trailing comment
        } // end comment
        """
        parse_success(parser, code)


class TestRealWorldExamples:
    """Test real-world OpenSCAD code examples."""

    def test_parametric_box(self, parser):
        """Test parametric box module."""
        code = """
        module box(width, height, depth, wall_thickness=1) {
            difference() {
                cube([width, height, depth]);
                translate([wall_thickness, wall_thickness, wall_thickness]) {
                    cube([width - 2*wall_thickness, 
                          height - 2*wall_thickness, 
                          depth - wall_thickness]);
                }
            }
        }
        """
        parse_success(parser, code)

    def test_spiral_array(self, parser):
        """Test spiral array pattern."""
        code = """
        module spiral_array(count=10, radius=10, height=5) {
            for (i = [0:count-1]) {
                angle = i * 360 / count;
                x = radius * cos(angle);
                y = radius * sin(angle);
                translate([x, y, height * i / count]) {
                    rotate([0, 0, angle]) cube(1);
                }
            }
        }
        """
        parse_success(parser, code)

    def test_helper_functions(self, parser):
        """Test helper function definitions."""
        code = """
        function deg_to_rad(deg) = deg * PI / 180;
        function rad_to_deg(rad) = rad * 180 / PI;
        function clamp(value, min_val, max_val) = 
            value < min_val ? min_val : 
            value > max_val ? max_val : value;
        """
        parse_success(parser, code)

    def test_list_utilities(self, parser):
        """Test list utility functions."""
        code = """
        function sum(list) = 
            len(list) > 0 ? 
                list[0] + sum([for (i = [1:len(list)-1]) list[i]]) : 
                0;
        
        function max(list) = 
            len(list) > 0 ?
                let(m = max([for (i = [1:len(list)-1]) list[i]]))
                list[0] > m ? list[0] : m :
                undef;
        """
        parse_success(parser, code)


class TestParserModes:
    """Test different parser modes."""

    def test_reduced_tree_mode(self, parser_reduced):
        """Test parser with reduced tree."""
        code = "x = 1 + 2;"
        parse_success(parser_reduced, code)

    def test_reduced_tree_complex(self, parser_reduced):
        """Test reduced tree with complex code."""
        code = """
        module test(x) {
            for (i = [0:5]) {
                translate([i, 0, 0]) cube(1);
            }
        }
        """
        parse_success(parser_reduced, code)

