# OpenSCAD Parser Test Suite

This directory contains a comprehensive test suite for the OpenSCAD parser.

## Test Organization

The test suite is organized into the following modules:

- **test_lexical.py**: Tests for basic lexical elements (comments, strings, numbers, identifiers, booleans, undef)
- **test_use_include.py**: Tests for `use` and `include` statements
- **test_modules.py**: Tests for module definitions and instantiations, including modifiers
- **test_functions.py**: Tests for function definitions and calls, including function literals
- **test_control_structures.py**: Tests for control structures (if/else, for, intersection_for, let, assert, echo, each)
- **test_expressions.py**: Tests for expressions and operator precedence
- **test_vectors.py**: Tests for vectors, ranges, and list comprehensions
- **test_assignments.py**: Tests for assignments and statements
- **test_complex.py**: Tests for complex scenarios, edge cases, and real-world examples
- **test_ast_generation.py**: Tests for AST generation from parse trees
- **test_ast_convenience.py**: Tests for convenience functions (getASTfromString, getASTfromFile, etc.)
- **test_builder.py**: Tests for the AST builder functionality
- **test_nodes.py**: Tests for AST node types and their properties
- **test_serialization.py**: Tests for JSON and YAML serialization/deserialization of AST trees
- **test_source_map.py**: Tests for source position tracking and source maps

## Running the Tests

### Prerequisites

Install the development dependencies:

```bash
pip install -e ".[dev]"
```

Or install pytest directly:

```bash
pip install pytest
```

### Running All Tests

```bash
pytest tests/
```

### Running Specific Test Files

```bash
pytest tests/test_lexical.py
pytest tests/test_modules.py
```

### Running Specific Test Classes

```bash
pytest tests/test_lexical.py::TestComments
```

### Running Specific Tests

```bash
pytest tests/test_lexical.py::TestComments::test_single_line_comment
```

### Verbose Output

```bash
pytest tests/ -v
```

### With Coverage

```bash
pip install pytest-cov
pytest tests/ --cov=openscad_parser --cov-report=html
```

## Test Structure

Each test file follows a similar structure:

- Test classes group related tests
- Each test method tests a specific feature or scenario
- Tests use helper functions from `conftest.py`:
  - `parse_success(parser, code)`: Asserts that code parses successfully
  - `parse_failure(parser, code)`: Asserts that code fails to parse

## Fixtures

The test suite provides the following fixtures (defined in `conftest.py`):

- `parser`: A parser instance with `reduce_tree=False`
- `parser_reduced`: A parser instance with `reduce_tree=True`

## Coverage

The test suite aims to cover:

- ✅ All lexical elements (comments, strings, numbers, identifiers, etc.)
- ✅ Use and include statements
- ✅ Module definitions and instantiations
- ✅ Function definitions and calls
- ✅ All control structures
- ✅ Expression parsing and operator precedence
- ✅ Vectors and list comprehensions
- ✅ AST generation and node types
- ✅ AST serialization (JSON and YAML)
- ✅ Source position tracking
- ✅ Edge cases and complex scenarios
- ✅ Real-world OpenSCAD code examples

## Adding New Tests

When adding new tests:

1. Add tests to the appropriate test file, or create a new one if needed
2. Follow the existing naming conventions
3. Use descriptive test names and docstrings
4. Test both success and failure cases where appropriate
5. Include edge cases and boundary conditions


