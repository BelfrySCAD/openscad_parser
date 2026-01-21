# Product Requirements Document: OpenSCAD Parser

## Overview

**Project:** OpenSCAD Parser
**Version:** 2.0.0
**Status:** Beta
**License:** MIT

OpenSCAD Parser is a Python library that parses OpenSCAD language source code using a PEG (Parsing Expression Grammar) approach and generates an Abstract Syntax Tree (AST) for programmatic analysis and manipulation.

## Problem Statement

OpenSCAD is a popular programming language for creating parametric 3D CAD models. However, there is limited tooling for programmatically analyzing, transforming, or working with OpenSCAD source code. Developers building tools like:

- Code editors and IDE plugins
- Linters and static analyzers
- Code formatters
- Refactoring tools
- Documentation generators
- Model converters

...need a reliable parser that produces a well-structured AST with accurate source position tracking.

## Target Users

### Primary Personas

1. **Tool Developers** - Building IDE plugins, linters, formatters, or other developer tools for OpenSCAD
2. **Library Authors** - Creating higher-level abstractions on top of OpenSCAD
3. **Researchers** - Analyzing OpenSCAD codebases for patterns, complexity metrics, or academic study
4. **Automation Engineers** - Building pipelines that programmatically modify or generate OpenSCAD models

### User Needs

| Need | Priority |
|------|----------|
| Parse valid OpenSCAD code into a traversable structure | Critical |
| Accurate source position tracking for error reporting | High |
| Handle include/use statements correctly | High |
| Support comments in AST for documentation tools | Medium |
| Parse invalid code gracefully with useful errors | Medium |

## Current Capabilities (v2.0.0)

### Language Support

Full parsing support for OpenSCAD language constructs:

- **Declarations**: Module definitions, function definitions, variable assignments
- **Expressions**: Arithmetic, logical, comparison, bitwise, ternary operators with correct precedence
- **Literals**: Numbers, strings, booleans, vectors, ranges
- **Control Structures**: if/else, for loops, let expressions, assert, echo
- **Module System**: Module calls with modifiers (!, #, %, *), use/include statements
- **Advanced**: List comprehensions, nested expressions, complex nesting

### Core Features

| Feature | Description |
|---------|-------------|
| PEG Grammar | Complete grammar covering OpenSCAD language (~420 rules) |
| AST Generation | Dataclass-based nodes for all language constructs |
| Source Mapping | Track positions across multiple files (essential for includes) |
| Caching | In-memory AST cache with modification time validation |
| Library Resolution | Platform-aware search paths matching OpenSCAD behavior |
| Comment Preservation | Optional inclusion of comments in AST |

### API Surface

```python
# High-level convenience functions
from openscad_parser.ast import (
    getASTfromString,      # Parse code from string
    getASTfromFile,        # Parse file with caching
    getASTfromLibraryFile, # Resolve and parse library files
    findLibraryFile,       # Locate library files
    clear_ast_cache,       # Clear AST cache
)

# Lower-level access
from openscad_parser import getOpenSCADParser
from openscad_parser.ast import parse_ast
```

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Code                               │
├─────────────────────────────────────────────────────────────┤
│  Convenience API: getASTfromString, getASTfromFile, etc.    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │   Parser    │───►│ Parse Tree  │───►│ ASTBuilder      │ │
│  │ (Arpeggio)  │    │             │    │ (Visitor)       │ │
│  └─────────────┘    └─────────────┘    └─────────────────┘ │
│         │                                      │            │
│         ▼                                      ▼            │
│  ┌─────────────┐                      ┌─────────────────┐  │
│  │  grammar.py │                      │   AST Nodes     │  │
│  │ (PEG rules) │                      │  (dataclasses)  │  │
│  └─────────────┘                      └─────────────────┘  │
│                                                │            │
│                                       ┌────────┴────────┐  │
│                                       │   SourceMap     │  │
│                                       │ (position track)│  │
│                                       └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | File | Responsibility |
|-----------|------|----------------|
| Grammar | `grammar.py` | PEG parsing rules for OpenSCAD syntax |
| AST Nodes | `ast/nodes.py` | Dataclass definitions for all node types |
| Builder | `ast/builder.py` | Visitor that converts parse tree to AST |
| Source Map | `ast/source_map.py` | Tracks positions across multiple origins |
| API | `ast/__init__.py` | Public convenience functions |

## Quality Attributes

### Performance
- Parser memoization via Arpeggio
- AST caching with modification time validation
- Efficient source map lookups

### Reliability
- Comprehensive test suite (~200+ tests)
- Tests organized by language feature
- No known parsing failures for valid OpenSCAD code

### Usability
- Simple high-level API for common use cases
- Lower-level access available when needed
- Accurate error messages with source positions

### Maintainability
- Clean separation between parsing and AST construction
- Dataclass-based nodes are easy to extend
- Type hints throughout codebase

## Future Directions

The following are potential enhancements for contributors to consider:

### High Value

| Enhancement | Description | Rationale |
|-------------|-------------|-----------|
| **AST Serialization** | JSON/YAML export of AST | Enable language-agnostic tooling |
| **Code Generation** | AST to OpenSCAD source | Enable refactoring tools, formatters |
| **Error Recovery** | Parse partial/invalid code | Better IDE integration, real-time parsing |
| **Semantic Analysis** | Type inference, scope resolution | Enable advanced linting, autocomplete |

### Medium Value

| Enhancement | Description | Rationale |
|-------------|-------------|-----------|
| **AST Diffing** | Compare two ASTs structurally | Enable change detection tools |
| **Tree Walkers** | Pre-built visitor utilities | Reduce boilerplate for common traversals |
| **Pretty Printer** | Configurable code formatting | Standardize code style |
| **Symbol Table** | Track variable/function definitions | Enable go-to-definition, find-references |

### Lower Priority

| Enhancement | Description | Rationale |
|-------------|-------------|-----------|
| **Language Server Protocol** | LSP implementation | Full IDE integration |
| **Incremental Parsing** | Re-parse only changed sections | Performance for large files |
| **Custom Extensions** | Support for OpenSCAD variants | Handle customizer syntax, etc. |

## Success Metrics

For open source contributors, consider these indicators of project health:

| Metric | Current | Notes |
|--------|---------|-------|
| Test Coverage | High | Comprehensive suite, no skipped tests |
| Documentation | Good | README, docstrings, source map guide |
| API Stability | Improving | v2.0.0 indicates recent breaking changes |
| Dependencies | Minimal | Only Arpeggio required |

## Contributing

### Good First Issues

- Add JSON serialization for AST nodes
- Create utility functions for common AST traversals
- Improve error messages for parse failures
- Add examples for common use cases

### Development Setup

```bash
git clone https://github.com/belfryscad/openscad_parser.git
cd openscad_parser
pip install -e ".[dev]"
pytest tests/
```

### Code Style

- Use type hints for all public APIs
- Follow existing patterns for AST node definitions
- Add tests for any new functionality
- Keep dependencies minimal

## References

- [OpenSCAD Language Reference](https://openscad.org/documentation.html)
- [Arpeggio PEG Parser](https://github.com/textX/Arpeggio)
- [Project Repository](https://github.com/belfryscad/openscad_parser)
