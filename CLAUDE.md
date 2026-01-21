# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenSCAD Parser is a PEG parser for the OpenSCAD language written in Python. It parses OpenSCAD source code and generates an Abstract Syntax Tree (AST) for programmatic analysis and manipulation. Built on the Arpeggio parsing library.

## Build & Test Commands

```bash
# Install with development dependencies
pip install -e ".[dev]"
# Or with uv:
uv pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_lexical.py

# Run specific test
pytest tests/test_lexical.py::TestComments::test_single_line_comment

# Build package
uv build
```

## Architecture

### Core Modules

**Parser Layer** (`src/openscad_parser/`):
- `__init__.py` - Exports `getOpenSCADParser()` which creates Arpeggio parser instances
- `grammar.py` - Complete PEG grammar for OpenSCAD (~420 lines of parsing rules)

**AST Layer** (`src/openscad_parser/ast/`):
- `nodes.py` - Dataclass definitions for all AST node types (literals, operators, expressions, modules, declarations, comments)
- `builder.py` - `ASTBuilderVisitor` that converts Arpeggio parse trees to AST using visitor pattern
- `source_map.py` - `SourceMap` class for tracking source positions across multiple origins (essential for include statements)
- `serialization.py` - Support for serializing ASTs to JSON or YAML.
- `__init__.py` - Public API: `getASTfromString()`, `getASTfromFile()`, `getASTfromLibraryFile()`, `parse_ast()`

### Data Flow

1. Source code → `getOpenSCADParser()` creates Arpeggio parser
2. Parser applies PEG grammar from `grammar.py` → parse tree
3. `ASTBuilderVisitor` traverses parse tree → AST nodes
4. `SourceMap` maintains position tracking throughout

### Key Design Patterns

- **Caching**: AST results are cached in-memory with modification time validation. Use `clear_ast_cache()` to clear.
- **Include processing**: `process_includes=True` (default) expands include statements before parsing. Set to `False` to preserve `IncludeStatement` nodes.
- **Library resolution**: `findLibraryFile()` and `getASTfromLibraryFile()` use platform-aware search paths (OPENSCADPATH env var, then platform defaults).

## Test Organization

Tests in `tests/` are organized by feature:
- `test_lexical.py` - Comments, strings, numbers, identifiers
- `test_modules.py`, `test_functions.py` - Module/function definitions and calls
- `test_expressions.py` - Expressions and operator precedence
- `test_control_structures.py` - If/else, for loops, let, assert, echo
- `test_ast_generation.py`, `test_builder.py`, `test_nodes.py` - AST internals
- `test_source_map.py` - Source position tracking

Fixtures in `conftest.py`: `parser` (full tree), `parser_reduced` (reduced tree).
