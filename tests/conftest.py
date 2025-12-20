"""Pytest configuration and shared fixtures for OpenSCAD parser tests."""

import pytest
from openscad_parser import getOpenSCADParser


@pytest.fixture
def parser():
    """Create a parser instance for testing."""
    return getOpenSCADParser(reduce_tree=False)


@pytest.fixture
def parser_reduced():
    """Create a parser instance with reduced tree for testing."""
    return getOpenSCADParser(reduce_tree=True)


def parse_success(parser, code):
    """Helper function to parse code and assert success."""
    result = parser.parse(code)
    assert result is not None
    return result


def parse_failure(parser, code):
    """Helper function to parse code and assert failure."""
    with pytest.raises(Exception):
        parser.parse(code)


