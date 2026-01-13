# Source Map Usage Example

The `SourceMap` class allows you to combine multiple source origins (files, editor buffers, etc.) into a single string for parsing while maintaining the ability to map positions back to their original source locations. This is essential for handling OpenSCAD's `include` statements, which can appear at any scope.

## Basic Usage

```python
from openscad_parser.ast.source_map import SourceMap
from openscad_parser import getOpenSCADParser
from openscad_parser.ast import parse_ast
from arpeggio import NoMatch

# Create a source map
source_map = SourceMap()

# Add the main file
source_map.add_origin("main.scad", "x = 5;\ninclude <lib.scad>\ny = 10;\n")

# Find where the include statement is (position 8 in this case)
include_pos = 8  # Position of "include <lib.scad>"

# Add the included file at that position
source_map.add_origin("lib.scad", "z = 20;\n", insert_at=include_pos)

# Get the combined string for parsing
combined_code = source_map.get_combined_string()
# Result: "x = 5;\nz = 20;\ny = 10;\n"

# Parse the combined code
parser = getOpenSCADParser()
try:
    ast = parse_ast(parser, combined_code)
except NoMatch as e:
    # Map the error position back to the original source
    error_pos = e.position.position  # Character position in combined string
    location = source_map.get_location(error_pos)
    print(f"Syntax error in {location.origin} at line {location.line}, column {location.column}")
```

## Handling Include Statements

When processing OpenSCAD code with `include` statements, you would:

1. Parse the main file to find `include` statements
2. For each `include`, load the included file
3. Insert the included file's content at the position of the `include` statement
4. Parse the combined string
5. When errors occur, use `get_location()` to report the correct source location

## Example: Processing a File with Includes

```python
from openscad_parser.ast.source_map import SourceMap
from openscad_parser import getOpenSCADParser
from openscad_parser.ast import parse_ast, getASTfromFile
from openscad_parser.ast.nodes import IncludeStatement

def parse_with_includes(main_file: str) -> list:
    """Parse a file and all its includes, returning AST with proper source locations."""
    source_map = SourceMap()
    
    # Load main file
    with open(main_file, 'r') as f:
        main_content = f.read()
    
    source_map.add_origin(main_file, main_content)
    
    # Parse to find include statements
    parser = getOpenSCADParser()
    ast = parse_ast(parser, main_content, file=main_file)
    
    # Process includes (simplified - you'd need to track positions more carefully)
    if isinstance(ast, list):
        for node in ast:
            if isinstance(node, IncludeStatement):
                # Load included file
                included_file = node.filename  # You'd extract this from the AST
                with open(included_file, 'r') as f:
                    included_content = f.read()
                
                # Insert at the position of the include statement
                # (You'd need to track the position from the AST node)
                include_pos = node.position.position
                source_map.add_origin(included_file, included_content, insert_at=include_pos)
    
    # Get combined string and re-parse
    combined = source_map.get_combined_string()
    combined_ast = parse_ast(parser, combined, file=main_file)
    
    return combined_ast, source_map

# Usage
ast, source_map = parse_with_includes("main.scad")

# If an error occurs during parsing:
try:
    # ... parsing code ...
    pass
except NoMatch as e:
    error_pos = e.position.position
    location = source_map.get_location(error_pos)
    print(f"Error in {location.origin}:{location.line}:{location.column}")
```

## Example: Using Generic Origins

The source map supports any origin identifier, not just file paths. This is useful for editor buffers, generated code, etc.:

```python
from openscad_parser.ast.source_map import SourceMap

source_map = SourceMap()

# Add a file
source_map.add_origin("main.scad", "x = 5;\n")

# Add content from an editor buffer
source_map.add_origin("<editor>", "y = 10;\n", insert_at=8)

# Add generated code
source_map.add_origin("<generated>", "z = 20;\n", insert_at=20)

# When reporting errors, the origin will be preserved
location = source_map.get_location(15)
print(f"Error in {location.origin}")  # Could be "<editor>", "main.scad", etc.
```

## API Reference

### `SourceMap`

Main class for managing source maps.

#### Methods

- `add_origin(origin: str, content: str, insert_at: Optional[int] = None, start_line: int = 1, start_column: int = 1) -> int`
  - Add a source origin's content to the source map
  - `origin` can be any identifier (file path, `"<editor>"`, `"<generated>"`, etc.)
  - Returns the position where the origin was inserted

- `get_combined_string() -> str`
  - Get the combined source string from all added origins

- `get_location(position: int) -> SourceLocation`
  - Get the original source location for a position in the combined string
  - Returns a `SourceLocation` with `origin`, `line`, and `column` attributes

- `get_segments() -> list[SourceSegment]`
  - Get all source segments (for debugging/inspection)

### `SourceLocation`

Represents a location in a source origin.

- `origin: str` - Identifier for the source origin (e.g., file path, `"<editor>"`, etc.)
- `line: int` - Line number (1-indexed)
- `column: int` - Column number (1-indexed)

### `SourceSegment`

Represents a segment of source code (internal use).

### Helper Functions

- `create_source_map_from_origins(origins: list[Tuple[str, str]], insert_positions: Optional[list[int]] = None) -> SourceMap`
  - Create a SourceMap from a list of `(origin, content)` tuples
  - Useful for batch creation of source maps

## Notes

- Positions are 0-indexed in the combined string
- Line and column numbers are 1-indexed in the returned locations
- When inserting origins, subsequent segments are automatically shifted
- Gaps between segments are filled with spaces in the combined string
- Origin identifiers can be any string - use descriptive names like `"<editor>"`, `"<generated>"`, file paths, etc.