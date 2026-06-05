"""Tests for lexical elements: comments, strings, numbers, identifiers."""

from arpeggio import ParserPython
import pytest
from openscad_parser import getOpenSCADParser
from tests.conftest import parse_failure, parse_success


class TestComments:
    """Test comment parsing."""

    def test_single_line_comment(self, parser, parser_comments):
        """Test single-line comments."""
        code = "// This is a comment"
        parse_success(parser, code, "")
        parse_success(parser_comments, code, "// This is a comment | ")

    def test_single_line_comment_with_code(self, parser, parser_comments):
        """Test single-line comment with code before it."""
        code = "x = 5; // comment"
        parse_success(parser, code, "x | = | 5 | ; | ")
        parse_success(parser_comments, code, "x | = | 5 | ; | // comment | ")

    def test_multi_line_comment(self, parser, parser_comments):
        """Test multi-line comments."""
        code = "/* This is a\nmulti-line comment */"
        parse_success(parser, code, "")
        parse_success(parser_comments, code, "/* This is a\nmulti-line comment */ | ")

    def test_multi_line_comment_single_line(self, parser, parser_comments):
        """Test multi-line comment on single line."""
        code = "/* comment */"
        parse_success(parser, code, "")
        parse_success(parser_comments, code, "/* comment */ | ")

    def test_comments_in_expressions(self, parser, parser_comments):
        """Test comments within expressions."""
        code = "x = 1 + /* comment */ 2;"
        parse_success(parser, code, "x | = | 1 | + | 2 | ; | ")
        # parse_success(parser_comments, code) # Broken

    def test_block_comment_followed_by_block_comment(self, parser, parser_comments):
        """Test block comment followed by another block comment"""
        code = "/* comment *//* another comment */"
        parse_success(parser, code, "")
        parse_success(parser_comments, code, "/* comment */ | /* another comment */ | ")

    def test_block_comment_followed_by_inline_comment(self, parser, parser_comments):
        """Test block comment followed by an inline comment"""
        code = "/* comment */// another comment"
        parse_success(parser, code, "")
        parse_success(parser_comments, code, "/* comment */ | // another comment | ")

    def test_inline_comment_with_nested_inline(self, parser, parser_comments):
        """Test an inline comment with a nested inline gets parsed as just one comment"""
        code = "// comment // the same comment"
        parse_success(parser, code, "")
        parse_success(parser_comments, code, "// comment // the same comment | ")

    def test_inline_comment_with_nested_block_comment(self, parser, parser_comments):
        """Test an inline comment with a nested block comment gets parsed as just one comment"""
        code = "// comment /* the same comment */"
        parse_success(parser, code, "")
        parse_success(parser_comments, code, "// comment /* the same comment */ | ")

    def test_inline_comment_with_nested_unclosed_block_comment(self, parser, parser_comments):
        """Test an inline comment with a nested unclosed block comment gets parsed as just one comment"""
        code = "// comment /* the same comment"
        parse_success(parser, code, "")
        parse_success(parser_comments, code, "// comment /* the same comment | ")

    def test_block_comment_with_unclosed_nested_block_comment(self, parser, parser_comments):
        """Test that a block comment with a nested unclosed block comment gets parsed as just one comment"""
        code = "/* comment /* the same comment */"
        parse_success(parser, code, "")
        parse_success(parser_comments, code, "/* comment /* the same comment */ | ")

    def test_block_comment_with_nested_block_comment(self, parser, parser_comments):
        """Test that an invalid nested block comment with two close tokens fails to parse"""
        code = "/* comment /* the same comment */*/"
        parse_failure(parser, code)
        parse_failure(parser_comments, code)


    @pytest.mark.parametrize("i", list(range(40)))
    def test_comments_everywhere(self, i, parser, parser_comments):
        """Tests that comments in multiple possible lexical locations are parsed
        correctly. Comments that can be parsed correctly using include_comments
        are included in the `successfully_parsed_locations_when_include_comments_is_set`
        variable. Every value not in this list does not parse correctly when
        include_comments is set to true on the parser"""
        successfully_parsed_locations_when_include_comments_is_set = {
            0, 7, 8, 16, 24, 25, 26, 34, 35, 36, 37, 38, 39,
            # 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23, 27, 28, 29, 30, 31, 32, 33 # Broken
        }

        possible_comment_location_count = 40

        # A simple OpenSCAD module with various types of calls, and various
        # marked where comments could be added.
        code_template = "\n".join([
            "{0}module {1}test{2}({3}x,{4} y{5}) {6}{{{7}",
            "    {8}translate{9}({10}[{11}0, {12}1, {13}2{14}]{15}){16} rotate{17}({18}[{19}3,{20} 4,{21} 5{22}]{23}){24} {{{25}",
            "            {26}cube{27}({28}[{29}10, {30}11, {31}12{32}]{33}){34};{35}",
            "        {36}}}{37}",
            "{38}}}{39}",
            ""
        ])
        # The associated arpeggio parse tree string to the OpenSCAD module with
        # the same marked locations where comments could be added.
        parse_tree_template = "{0}module | {1}test | {2}( | {3}x | , | {4}y | {5}) | {6}{{ | {7}{8}translate | {9}( | {10}[ | {11}0 | , | {12}1 | , | {13}2 | {14}] | {15}) | {16}rotate | {17}( | {18}[ | {19}3 | , | {20}4 | , | {21}5 | {22}] | {23}) | {24}{{ | {25}{26}cube | {27}( | {28}[ | {29}10 | , | {30}11 | , | {31}12 | {32}] | {33}) | {34}; | {35}{36}}} | {37}{38}}} | {39}"

        empty_args = [''] * possible_comment_location_count
        parse_tree = parse_tree_template.format(*empty_args)

        # Test Block Comments
        block_code_args = empty_args.copy()
        block_code_args[i] = "/* Comment */"
        block_code = code_template.format(*block_code_args)

        block_tree_args = empty_args.copy()
        block_tree_args[i] = "/* Comment */ | "
        block_tree = parse_tree_template.format(*block_tree_args)

        parse_success(parser, block_code, parse_tree)
        if i in successfully_parsed_locations_when_include_comments_is_set:
            parse_success(parser_comments, block_code, block_tree)
        else:
            parse_failure(parser_comments, block_code)

        # Test Inline Comments
        inline_code_args = empty_args.copy()
        inline_code_args[i] = "// Comment\n"
        inline_code = code_template.format(*inline_code_args)

        inline_tree_args = empty_args.copy()
        inline_tree_args[i] = "// Comment | "
        inline_tree = parse_tree_template.format(*inline_tree_args)

        parse_success(parser, inline_code, parse_tree)
        if i in successfully_parsed_locations_when_include_comments_is_set:
            parse_success(parser_comments, inline_code, inline_tree)
        else:
            parse_failure(parser_comments, inline_code)


class TestStrings:
    """Test string literal parsing."""

    def test_single_quoted_string_rejected(self, parser):
        """Test that single-quoted strings are rejected (OpenSCAD only supports double quotes)."""
        from tests.conftest import parse_failure
        code = "x = 'hello';"
        parse_failure(parser, code)

    def test_double_quoted_string(self, parser):
        """Test double-quoted strings."""
        code = 'x = "hello";'
        parse_success(parser, code)

    def test_string_with_escapes(self, parser):
        """Test strings with escape sequences."""
        code = 'x = "hello\\nworld";'
        parse_success(parser, code)

    def test_string_with_quotes(self, parser):
        """Test strings containing quotes."""
        code = 'x = "say \\"hello\\"";'
        parse_success(parser, code)

    def test_empty_string(self, parser):
        """Test empty strings."""
        code = 'x = "";'
        parse_success(parser, code)

    def test_empty_string_ast(self):
        """Empty string literal produces StringLiteral(val='')."""
        import tempfile
        import os
        from openscad_parser.ast import getASTfromFile
        from openscad_parser.ast.nodes import StringLiteral, Assignment
        code = 'x = "";'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            f.write(code)
            fname = f.name
        nodes = getASTfromFile(fname, process_includes=False)
        os.unlink(fname)
        assignment = nodes[0]
        assert isinstance(assignment, Assignment)
        assert isinstance(assignment.expr, StringLiteral)
        assert assignment.expr.val == ""

    def test_empty_string_round_trip(self):
        """Empty string literal round-trips as \"\" not \"\" | \"\"."""
        import tempfile
        import os
        from openscad_parser.ast import getASTfromFile
        from openscad_parser.ast.pretty_print import to_openscad
        code = 'x = "";'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            f.write(code)
            fname = f.name
        output = to_openscad(getASTfromFile(fname, process_includes=False))
        os.unlink(fname)
        assert '"" | ""' not in output, f"Bug still present: {output!r}"
        assert '""' in output


class TestNumbers:
    """Test number literal parsing."""

    def test_integer(self, parser):
        """Test integer numbers."""
        code = "x = 42;"
        parse_success(parser, code)

    def test_negative_integer(self, parser):
        """Test negative integers."""
        code = "x = -42;"
        parse_success(parser, code)

    def test_positive_integer(self, parser):
        """Test explicitly positive integers."""
        code = "x = +42;"
        parse_success(parser, code)

    def test_float(self, parser):
        """Test floating point numbers."""
        code = "x = 3.14;"
        parse_success(parser, code)

    def test_float_no_leading_zero(self, parser):
        """Test floats without leading zero."""
        code = "x = .5;"
        parse_success(parser, code)

    def test_scientific_notation(self, parser):
        """Test scientific notation."""
        code = "x = 1e10;"
        parse_success(parser, code)

    def test_scientific_notation_negative(self, parser):
        """Test negative scientific notation."""
        code = "x = 1e-10;"
        parse_success(parser, code)

    def test_scientific_notation_positive(self, parser):
        """Test positive scientific notation."""
        code = "x = 1e+10;"
        parse_success(parser, code)

    def test_hexadecimal(self, parser):
        """Test hexadecimal numbers."""
        code = "x = 0xFF;"
        parse_success(parser, code)

    def test_hexadecimal_lowercase(self, parser):
        """Test lowercase hexadecimal numbers."""
        code = "x = 0xff;"
        parse_success(parser, code)


class TestIdentifiers:
    """Test identifier parsing."""

    def test_simple_identifier(self, parser):
        """Test simple identifiers."""
        code = "x = 1;"
        parse_success(parser, code)

    def test_identifier_with_underscore(self, parser):
        """Test identifiers with underscores."""
        code = "my_var = 1;"
        parse_success(parser, code)

    def test_identifier_with_numbers(self, parser):
        """Test identifiers with numbers."""
        code = "var1 = 1;"
        parse_success(parser, code)

    def test_identifier_dollar_sign(self, parser):
        """Test identifiers starting with dollar sign."""
        code = "$var = 1;"
        parse_success(parser, code)

    def test_identifier_mixed_case(self, parser):
        """Test mixed case identifiers."""
        code = "myVariable = 1;"
        parse_success(parser, code)

    def test_identifier_leading_underscore(self, parser):
        """Test identifiers starting with underscore."""
        code = "_private_var = 1;"
        parse_success(parser, code)

    def test_identifier_leading_underscore_uppercase(self, parser):
        """Test uppercase identifiers starting with underscore."""
        code = "_UNDEF = 1;"
        parse_success(parser, code)

    def test_identifier_double_underscore(self, parser):
        """Test identifiers starting with double underscore."""
        code = "__internal = 1;"
        parse_success(parser, code)

    def test_identifier_underscore_with_dollar(self, parser):
        """Test identifiers with dollar sign and underscore."""
        code = "$_special = 1;"
        parse_success(parser, code)

    def test_identifier_underscore_in_function(self, parser):
        """Test underscore-prefixed function names."""
        code = "function _helper(x) = x + 1;"
        parse_success(parser, code)

    def test_identifier_underscore_in_module(self, parser):
        """Test underscore-prefixed module names."""
        code = "module _internal() { cube(1); }"
        parse_success(parser, code)


class TestBooleans:
    """Test boolean literal parsing."""

    def test_true(self, parser):
        """Test true boolean."""
        code = "x = true;"
        parse_success(parser, code)

    def test_false(self, parser):
        """Test false boolean."""
        code = "x = false;"
        parse_success(parser, code)


class TestUndef:
    """Test undef literal parsing."""

    def test_undef(self, parser):
        """Test undef literal."""
        code = "x = undef;"
        parse_success(parser, code)


