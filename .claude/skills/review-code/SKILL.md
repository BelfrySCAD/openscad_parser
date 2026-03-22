---
name: review-code
description: Reviews code changes for bugs, style issues, and correctness. Use when reviewing code, PRs, or asking for a code review.
allowed-tools: Read, Grep, Glob, Bash
---

Review the code changes specified by `$ARGUMENTS` (a file path, directory, or git ref range). If no arguments are provided, review all uncommitted changes using `git diff` and `git diff --cached`.

## Review Checklist

### Correctness
- Logic errors, off-by-one mistakes, missing edge cases
- Proper handling of `None`/`undef` values throughout the AST pipeline
- Parse tree visitor methods in `builder.py` must match grammar rule names in `grammar.py`
- AST node dataclass fields must match what the builder produces

### Parser & Grammar
- New grammar rules must be reachable from `openscad_language` or `openscad_language_with_comments`
- Arpeggio ordering matters: alternatives are tried in order, put more specific rules first
- Ensure `comment` and `whitespace_only` skip rules aren't accidentally changed
- Token rules using `Not()` must not create ambiguity with other tokens

### AST Layer
- New node types must inherit from `ASTNode` and use `@dataclass`
- Nodes must be serializable (check `serialization.py` compatibility)
- Source position tracking via `SourceMap` must be preserved through transformations
- Scope handling: verify parent/child scope relationships are set correctly

### Python Style
- Type annotations on public API functions
- Dataclass fields should have sensible defaults where appropriate
- Avoid mutable default arguments (use `field(default_factory=...)`)
- Follow existing patterns in the codebase rather than introducing new conventions

### Testing
- New grammar rules need corresponding test cases in `tests/`
- Test both valid parses and expected parse failures
- AST builder changes need tests verifying node structure
- Use the existing `parser` and `parser_reduced` fixtures from `conftest.py`

## Output Format

Organize findings by severity:

1. **Bugs** - Will cause incorrect behavior or crashes
2. **Issues** - Could cause problems in some cases
3. **Suggestions** - Improvements to readability, style, or maintainability

For each finding, include the file path, line number, and a specific fix.
