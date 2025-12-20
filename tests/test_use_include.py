"""Tests for use and include statements."""

import pytest
from tests.conftest import parse_success


class TestUseStatement:
    """Test use statement parsing."""

    def test_use_simple(self, parser):
        """Test simple use statement."""
        code = "use <file.scad>"
        parse_success(parser, code)

    def test_use_with_path(self, parser):
        """Test use with path."""
        code = "use <lib/file.scad>"
        parse_success(parser, code)

    def test_use_multiple(self, parser):
        """Test multiple use statements."""
        code = "use <file1.scad>\nuse <file2.scad>"
        parse_success(parser, code)

    def test_use_with_code(self, parser):
        """Test use statement with code after."""
        code = "use <file.scad>\nx = 1;"
        parse_success(parser, code)


class TestIncludeStatement:
    """Test include statement parsing."""

    def test_include_simple(self, parser):
        """Test simple include statement."""
        code = "include <file.scad>"
        parse_success(parser, code)

    def test_include_with_path(self, parser):
        """Test include with path."""
        code = "include <lib/file.scad>"
        parse_success(parser, code)

    def test_include_multiple(self, parser):
        """Test multiple include statements."""
        code = "include <file1.scad>\ninclude <file2.scad>"
        parse_success(parser, code)

    def test_include_with_code(self, parser):
        """Test include statement with code after."""
        code = "include <file.scad>\nx = 1;"
        parse_success(parser, code)


class TestUseAndInclude:
    """Test mixing use and include statements."""

    def test_use_then_include(self, parser):
        """Test use followed by include."""
        code = "use <file1.scad>\ninclude <file2.scad>"
        parse_success(parser, code)

    def test_include_then_use(self, parser):
        """Test include followed by use."""
        code = "include <file1.scad>\nuse <file2.scad>"
        parse_success(parser, code)

    def test_multiple_mixed(self, parser):
        """Test multiple mixed use and include statements."""
        code = "use <file1.scad>\ninclude <file2.scad>\nuse <file3.scad>"
        parse_success(parser, code)


