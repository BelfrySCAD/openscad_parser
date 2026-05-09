"""Pytest configuration and shared fixtures for OpenSCAD parser tests."""

import pytest
from arpeggio import ParserPython
from openscad_parser import getOpenSCADParser
from typing import Optional

@pytest.fixture
def parser():
    """Create a parser instance for testing."""
    return getOpenSCADParser(reduce_tree=False)


@pytest.fixture
def parser_reduced():
    """Create a parser instance with reduced tree for testing."""
    return getOpenSCADParser(reduce_tree=True)


@pytest.fixture
def parser_comments():
    """Create a parser instance with comment inclusion enabled."""
    return getOpenSCADParser(reduce_tree=False, include_comments=True)


def parse_success(parser: ParserPython, code: str, expected_result: Optional[str] = None):
    """Helper function to parse code and assert success."""
    result = parser.parse(code)
    assert result is not None
    if expected_result is not None:
        assert str(result) == expected_result
    return result


def parse_failure(parser: ParserPython, code: str):
    """Helper function to parse code and assert failure."""
    with pytest.raises(Exception):
        parser.parse(code)


