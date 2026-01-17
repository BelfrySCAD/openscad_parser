"""Source map for tracking positions across multiple source origins.

This module provides functionality to combine multiple source origins (files,
editor buffers, etc.) into a single string for parsing while maintaining the
ability to map positions back to their original origin, line, and column locations.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .builder import Position


@dataclass
class SourceSegment:
    """Represents a segment of source code from a specific origin.
    
    Attributes:
        origin: Identifier for the source origin (e.g., file path, "<editor>", etc.)
        start_line: Starting line number in the original source (1-indexed)
        start_column: Starting column number in the original source (1-indexed)
        content: The source code content for this segment
        combined_start: Starting position in the combined string (0-indexed)
    """
    origin: str
    start_line: int
    start_column: int
    content: str
    combined_start: int  # Position in combined string where this segment starts


class SourceMap:
    """Maps positions in a combined source string back to original source locations.
    
    This class allows you to combine multiple source origins (e.g., from include
    statements, editor buffers, etc.) into a single string for parsing, while
    maintaining the ability to report accurate error locations in the original sources.
    
    Example:
        >>> source_map = SourceMap()
        >>> source_map.add_origin("main.scad", "x = 5;\\n")
        >>> source_map.add_origin("lib.scad", "y = 10;\\n", insert_at=8)
        >>> combined = source_map.get_combined_string()
        >>> location = source_map.get_location(15)  # Position in combined string
        >>> print(f"Error in {location.origin} at line {location.line}, column {location.column}")
    """
    
    def __init__(self):
        """Initialize an empty source map."""
        self._segments: list[SourceSegment] = []
        self._combined_string: str = ""
        self._combined_string_dirty: bool = True
    
    def add_origin(self, origin: str, content: str, insert_at: Optional[int] = None,
                   start_line: int = 1, start_column: int = 1, replace_length: int = 0,
                   strip_trailing_newline: bool = False) -> int:
        """Add a source origin's content to the source map.
        
        Args:
            origin: Identifier for the source origin (e.g., file path, "<editor>", etc.)
            content: The source content
            insert_at: Position in the combined string where this origin should be inserted.
                      If None, appends to the end. If specified, inserts at that position
                      and shifts subsequent segments.
            start_line: Starting line number in the original source (default: 1)
            start_column: Starting column number in the original source (default: 1)
            replace_length: If > 0, replace this many characters starting at insert_at
                           in the existing combined string before inserting the new content.
                           This is useful for replacing include statements with their content.
            strip_trailing_newline: If True and replace_length > 0, strip a leading newline
                                    from the content that comes after the replacement.
                                    Useful when the replacement content ends with a newline
                                    and you want to avoid double newlines.
        
        Returns:
            The starting position in the combined string where this origin was inserted
        """
        # If insert_at is None, append to the end
        if insert_at is None:
            # Calculate end position: max of all segment ends
            if self._segments:
                insert_at = max(seg.combined_start + len(seg.content) for seg in self._segments)
            else:
                insert_at = 0
        
        # If replace_length is specified, replace text in existing segments first
        if replace_length > 0:
            self._replace_text(insert_at, replace_length, strip_trailing_newline)
        
        # Create the segment
        segment = SourceSegment(
            origin=origin,
            start_line=start_line,
            start_column=start_column,
            content=content,
            combined_start=insert_at
        )
        
        # Insert the segment at the appropriate position (this will shift others)
        self._insert_segment(segment, insert_at)
        
        # Mark combined string as dirty
        self._combined_string_dirty = True
        
        return segment.combined_start
    
    def _replace_text(self, start_pos: int, length: int, strip_trailing_newline: bool = False):
        """Replace text in existing segments at the specified position.
        
        This modifies existing segments to remove the specified range of text.
        If the range spans multiple segments, they are adjusted accordingly.
        Segments that are split by the replacement are handled correctly.
        
        Args:
            start_pos: Starting position in the combined string (0-indexed)
            length: Number of characters to replace
        """
        if length <= 0:
            return
        
        end_pos = start_pos + length
        
        # Collect segments to modify and new segments to add (for splits)
        segments_to_remove = []
        new_segments = []
        
        for segment in self._segments:
            segment_start = segment.combined_start
            segment_end = segment_start + len(segment.content)
            
            # Check if segment overlaps with replacement range
            if segment_start < end_pos and segment_end > start_pos:
                # Calculate what part of this segment is being replaced
                replace_start_in_segment = max(0, start_pos - segment_start)
                replace_end_in_segment = min(len(segment.content), end_pos - segment_start)
                
                # Build new content by removing the replaced portion
                before_content = segment.content[:replace_start_in_segment]
                after_content = segment.content[replace_end_in_segment:]
                
                # If there's content before the replacement, keep the original segment (modified)
                if before_content:
                    segment.content = before_content
                    # Segment start stays the same
                else:
                    # No content before, mark segment for removal
                    segments_to_remove.append(segment)
                
                # If there's content after the replacement, create a new segment
                if after_content:
                    # If strip_trailing_newline is True and after_content starts with a newline, remove it
                    if strip_trailing_newline and after_content.startswith('\n'):
                        after_content = after_content[1:]
                        # Adjust line count for the removed newline
                        line_count_adjustment = 1
                    else:
                        line_count_adjustment = 0
                    
                    # Skip if after_content is now empty
                    if not after_content:
                        continue
                    
                    # Calculate the new start position for the after segment
                    # It should start at start_pos (where the replacement is)
                    after_segment = SourceSegment(
                        origin=segment.origin,
                        start_line=segment.start_line,
                        start_column=segment.start_column,
                        content=after_content,
                        combined_start=start_pos  # After replacement, this will be adjusted
                    )
                    # Calculate the actual line/column for the after segment
                    # Count lines in the part that was removed + before
                    removed_and_before = segment.content[:replace_end_in_segment]
                    line_count = removed_and_before.count('\n') - line_count_adjustment
                    if line_count > 0:
                        last_newline = removed_and_before.rfind('\n')
                        after_segment.start_line = segment.start_line + line_count
                        after_segment.start_column = len(removed_and_before) - last_newline
                    else:
                        after_segment.start_line = segment.start_line
                        after_segment.start_column = segment.start_column + len(removed_and_before)
                    
                    new_segments.append(after_segment)
        
        # Remove segments marked for removal
        for segment in segments_to_remove:
            if segment in self._segments:
                self._segments.remove(segment)
        
        # Add new segments (for the "after" parts)
        self._segments.extend(new_segments)
        
        # Remove segments that became empty
        self._segments = [seg for seg in self._segments if len(seg.content) > 0]
        
        # Shift all segments that come after the replacement to the left
        # Also adjust new segments that were created (they start at start_pos, need to account for removal)
        for segment in self._segments:
            if segment.combined_start >= end_pos:
                segment.combined_start -= length
            elif segment.combined_start == start_pos and segment in new_segments:
                # This is a new "after" segment - it's already at start_pos, which is correct
                # after the replacement (the removed text is gone, so start_pos is where it should be)
                pass
    
    def _insert_segment(self, segment: SourceSegment, insert_at: int):
        """Insert a segment at the specified position, shifting others as needed."""
        # Find all segments that need to be shifted (those starting at or after insert_at)
        segment_length = len(segment.content)
        
        # Shift segments that start at or after the insertion point
        for existing_segment in self._segments:
            if existing_segment.combined_start >= insert_at:
                existing_segment.combined_start += segment_length
        
        # Find the insertion index to maintain sorted order
        insert_idx = 0
        for i, existing_segment in enumerate(self._segments):
            if existing_segment.combined_start > segment.combined_start:
                insert_idx = i
                break
        else:
            insert_idx = len(self._segments)
        
        # Insert the new segment
        self._segments.insert(insert_idx, segment)
    
    def get_combined_string(self) -> str:
        """Get the combined source string from all added origins.
        
        Returns:
            The combined source string with all origins concatenated/inserted
        """
        if self._combined_string_dirty:
            self._rebuild_combined_string()
        return self._combined_string
    
    def _rebuild_combined_string(self):
        """Rebuild the combined string from segments."""
        if not self._segments:
            self._combined_string = ""
            self._combined_string_dirty = False
            return
        
        # Sort segments by their combined_start position
        sorted_segments = sorted(self._segments, key=lambda s: s.combined_start)
        
        # Build the combined string
        parts = []
        current_pos = 0
        
        for segment in sorted_segments:
            # Add any gap between segments
            if segment.combined_start > current_pos:
                parts.append(' ' * (segment.combined_start - current_pos))
            
            parts.append(segment.content)
            current_pos = segment.combined_start + len(segment.content)
        
        self._combined_string = ''.join(parts)
        self._combined_string_dirty = False
    
    def get_location(self, position: int):
        """Get the original source location for a position in the combined string.
        
        Args:
            position: Character position in the combined string (0-indexed)
        
        Returns:
            Position with origin, line, and column in the original source
        """
        from .builder import Position  # Lazy import to avoid circular dependency
        
        if position < 0:
            position = 0
        
        # Find the segment containing this position
        segment = self._find_segment(position)
        
        if segment is None:
            # Position is beyond all segments, return location from last segment
            if self._segments:
                last_segment = max(self._segments, key=lambda s: s.combined_start + len(s.content))
                return self._calculate_location_in_segment(last_segment, len(last_segment.content))
            else:
                return Position(origin="", line=1, column=1)
        
        # Calculate the position within the segment
        segment_offset = position - segment.combined_start
        return self._calculate_location_in_segment(segment, segment_offset)
    
    def _find_segment(self, position: int) -> Optional[SourceSegment]:
        """Find the segment containing the given position.
        
        Uses binary search for efficiency.
        """
        if not self._segments:
            return None
        
        # Binary search for the segment containing this position
        left, right = 0, len(self._segments) - 1
        
        while left <= right:
            mid = (left + right) // 2
            segment = self._segments[mid]
            segment_end = segment.combined_start + len(segment.content)
            
            if segment.combined_start <= position < segment_end:
                return segment
            elif position < segment.combined_start:
                right = mid - 1
            else:
                left = mid + 1
        
        # Check if position is in the last segment
        if self._segments:
            last_segment = self._segments[-1]
            if last_segment.combined_start <= position < last_segment.combined_start + len(last_segment.content):
                return last_segment
        
        return None
    
    def _calculate_location_in_segment(self, segment: SourceSegment, offset: int):
        """Calculate the source location for an offset within a segment.
        
        Args:
            segment: The source segment
            offset: Character offset within the segment (0-indexed)
        
        Returns:
            Position with the original source location
        """
        from .builder import Position  # Lazy import to avoid circular dependency
        
        if offset < 0:
            offset = 0  # pragma: no cover
        if offset > len(segment.content):
            offset = len(segment.content)  # pragma: no cover
        
        # Count lines in the content up to the offset
        content_before = segment.content[:offset]
        line_count = content_before.count('\n')
        
        # Calculate line number
        line_number = segment.start_line + line_count
        
        # Calculate column number
        if line_count == 0:
            # Same line as start
            column_number = segment.start_column + offset
        else:
            # Find the last newline before offset
            last_newline = content_before.rfind('\n')
            column_number = offset - last_newline
        
        return Position(
            origin=segment.origin,
            line=line_number,
            column=column_number
        )
    
    def get_segments(self) -> list[SourceSegment]:
        """Get all source segments.
        
        Returns:
            List of all source segments in order
        """
        return self._segments.copy()


def create_source_map_from_origins(origins: list[Tuple[str, str]], 
                                    insert_positions: Optional[list[int]] = None) -> SourceMap:
    """Create a SourceMap from a list of (origin, content) tuples.
    
    Args:
        origins: List of (origin, content) tuples
        insert_positions: Optional list of insertion positions for each origin.
                         If None, origins are appended sequentially.
                         If provided, must have same length as origins.
    
    Returns:
        A SourceMap with all origins added
    """
    source_map = SourceMap()
    
    if insert_positions is None:
        for origin, content in origins:
            source_map.add_origin(origin, content)
    else:
        if len(insert_positions) != len(origins):
            raise ValueError("insert_positions must have same length as origins")
        
        for (origin, content), insert_at in zip(origins, insert_positions):
            source_map.add_origin(origin, content, insert_at=insert_at)
    
    return source_map


def process_includes(source_map: SourceMap, current_file: str = "", 
                     max_iterations: int = 100) -> SourceMap:
    """Process all include statements in a SourceMap, replacing them with file contents.
    
    This function scans the combined source string for `include <filename>` patterns,
    ensures they're not inside strings or comments, loads the included files, and
    replaces the include statements with their content. This process repeats until
    no more include statements are found.
    
    Args:
        source_map: The SourceMap to process
        current_file: Path to the current file (used for resolving relative includes)
        max_iterations: Maximum number of iterations to prevent infinite loops (default: 100)
    
    Returns:
        The updated SourceMap with all includes processed
    
    Raises:
        FileNotFoundError: If an included file cannot be found
        ValueError: If max_iterations is exceeded (likely circular includes)
    
    Example:
        >>> from openscad_parser.ast.source_map import SourceMap, process_includes
        >>> source_map = SourceMap()
        >>> source_map.add_origin("main.scad", "x = 5;\\ninclude <lib.scad>\\n")
        >>> source_map = process_includes(source_map, "main.scad")
    """
    from . import findLibraryFile
    
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        combined = source_map.get_combined_string()
        
        # Find all include statements that are not in strings or comments
        includes = _find_valid_includes(combined)
        
        if not includes:
            # No more includes found, we're done
            break
        
        # Process includes in reverse order (from end to start) to maintain positions
        includes.sort(key=lambda x: x['position'], reverse=True)
        
        for include_info in includes:
            filename = include_info['filename']
            position = include_info['position']
            length = include_info['length']
            
            # Find the library file
            if current_file:
                # Use the directory of the current file as base
                lib_file = findLibraryFile(current_file, filename)
            else:
                # Try to find it without a current file context
                lib_file = findLibraryFile("", filename)
            
            if lib_file is None:
                raise FileNotFoundError(
                    f"Included file '{filename}' not found. "
                    f"Searched relative to: {current_file if current_file else 'current directory'}"
                )
            
            # Read the included file
            try:
                with open(lib_file, 'r', encoding='utf-8') as f:
                    included_content = f.read()
            except Exception as e:  # pragma: no cover
                raise IOError(f"Error reading included file '{lib_file}': {e}")
            
            # Get the origin of the segment containing this position
            location = source_map.get_location(position)
            origin = location.origin
            
            # Replace the include statement with the file content
            # Use strip_trailing_newline=True to avoid double newlines
            source_map.add_origin(
                origin=lib_file,
                content=included_content,
                insert_at=position,
                replace_length=length,
                strip_trailing_newline=True
            )
            
            # Update current_file to the included file for nested includes
            current_file = lib_file
    else:
        # We exited the loop due to max_iterations
        raise ValueError(
            f"Maximum iterations ({max_iterations}) exceeded while processing includes. "
            "This may indicate circular includes or a very deep include chain."
        )
    
    return source_map


def _find_valid_includes(code: str) -> list[dict]:
    """Find all valid include statements in code, excluding those in strings or comments.
    
    Args:
        code: The source code to scan
    
    Returns:
        List of dictionaries with 'position', 'length', and 'filename' keys
    """
    includes = []
    i = 0
    in_string = False
    string_char = None
    in_single_line_comment = False
    in_multi_line_comment = False
    
    while i < len(code):
        char = code[i]
        next_char = code[i + 1] if i + 1 < len(code) else None
        
        # Handle strings
        if not in_single_line_comment and not in_multi_line_comment:
            if char == '"' or char == "'":
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    # Check for escaped quote
                    if i > 0 and code[i - 1] != '\\':
                        in_string = False
                        string_char = None
            elif in_string and char == '\\' and next_char == string_char:
                # Escaped quote, skip the next character
                i += 1
        
        # Handle single-line comments
        if not in_string and not in_multi_line_comment:
            if char == '/' and next_char == '/':
                in_single_line_comment = True
                i += 1  # Skip the second '/'
            elif in_single_line_comment and char == '\n':
                in_single_line_comment = False
        
        # Handle multi-line comments
        if not in_string and not in_single_line_comment:
            if char == '/' and next_char == '*':
                in_multi_line_comment = True
                i += 1  # Skip the '*'
            elif in_multi_line_comment and char == '*' and next_char == '/':
                in_multi_line_comment = False
                i += 1  # Skip the '/'
        
        # Look for include statements (only if not in string or comment)
        if not in_string and not in_single_line_comment and not in_multi_line_comment:
            # Check for "include <"
            if (char == 'i' and 
                i + 7 < len(code) and 
                code[i:i+7] == 'include' and
                (i == 0 or not (code[i-1].isalnum() or code[i-1] == '_')) and  # Word boundary
                i + 8 < len(code)):
                
                # Check for whitespace after "include"
                after_include = _skip_whitespace(code, i + 7)
                if after_include < len(code) and code[after_include] == '<':
                    # Found "include <", now find the closing >
                    start_pos = i
                    filename_start = after_include + 1
                    filename_end = filename_start
                    
                    # Find the closing >
                    while filename_end < len(code) and code[filename_end] != '>':
                        if code[filename_end] == '\n':
                            # Include statement spans multiple lines, skip it
                            break
                        filename_end += 1
                    else:
                        # Found the closing >
                        if filename_end < len(code):
                            filename = code[filename_start:filename_end].strip()
                            if filename:
                                end_pos = filename_end + 1
                                includes.append({
                                    'position': start_pos,
                                    'length': end_pos - start_pos,
                                    'filename': filename
                                })
                                i = end_pos
                                continue
        
        i += 1
    
    return includes


def _skip_whitespace(code: str, start: int) -> int:
    """Skip whitespace characters starting from the given position.
    
    Args:
        code: The source code
        start: Starting position
    
    Returns:
        Position after skipping whitespace
    """
    i = start
    while i < len(code) and code[i] in ' \t\n\r':
        i += 1
    return i
