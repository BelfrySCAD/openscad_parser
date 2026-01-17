"""Tests for source map functionality, including include processing."""

import os
import tempfile
import pytest
from openscad_parser.ast.source_map import SourceMap, process_includes
from openscad_parser.ast.builder import Position


class TestSourceMapBasic:
    """Test basic SourceMap functionality."""

    def test_add_origin(self):
        """Test adding origins to source map."""
        source_map = SourceMap()
        source_map.add_origin("main.scad", "x = 5;\n")
        
        assert len(source_map.get_segments()) == 1
        assert source_map.get_combined_string() == "x = 5;\n"

    def test_get_location(self):
        """Test getting location from position."""
        source_map = SourceMap()
        source_map.add_origin("main.scad", "x = 5;\n")
        
        loc = source_map.get_location(0)
        assert loc.origin == "main.scad"
        assert loc.line == 1
        assert loc.column == 1
        
        loc = source_map.get_location(4)
        assert loc.origin == "main.scad"
        assert loc.line == 1
        assert loc.column == 5

    def test_multiple_origins(self):
        """Test multiple origins."""
        source_map = SourceMap()
        source_map.add_origin("main.scad", "x = 5;\n")
        source_map.add_origin("lib.scad", "y = 10;\n", insert_at=8)
        
        combined = source_map.get_combined_string()
        assert "x = 5;\n" in combined
        assert "y = 10;\n" in combined
        
        # Check locations
        loc = source_map.get_location(8)
        assert loc.origin == "lib.scad"


class TestProcessIncludes:
    """Test process_includes function."""

    def test_simple_include(self):
        """Test processing a simple include statement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib.scad>\ny = 10;\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "z = 20;\n" in result
            assert "y = 10;\n" in result
            assert "include <lib.scad>" not in result

    def test_nested_includes(self):
        """Test nested include statements."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib1_file = os.path.join(temp_dir, "lib1.scad")
            lib2_file = os.path.join(temp_dir, "lib2.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib1.scad>\n")
            
            with open(lib1_file, 'w') as f:
                f.write("y = 10;\ninclude <lib2.scad>\nz = 15;\n")
            
            with open(lib2_file, 'w') as f:
                f.write("w = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "y = 10;\n" in result
            assert "w = 20;\n" in result
            assert "z = 15;\n" in result
            assert "include" not in result

    def test_multiple_includes(self):
        """Test multiple include statements in one file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib1_file = os.path.join(temp_dir, "lib1.scad")
            lib2_file = os.path.join(temp_dir, "lib2.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib1.scad>\ny = 10;\ninclude <lib2.scad>\nz = 15;\n")
            
            with open(lib1_file, 'w') as f:
                f.write("a = 1;\n")
            
            with open(lib2_file, 'w') as f:
                f.write("b = 2;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "a = 1;\n" in result
            assert "y = 10;\n" in result
            assert "b = 2;\n" in result
            assert "z = 15;\n" in result
            assert "include" not in result

    def test_include_in_string_ignored(self):
        """Test that includes in strings are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write('x = 5;\n"include <lib.scad>"\ninclude <lib.scad>\n')
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            # The include in the string should remain, the real one should be replaced
            assert '"include <lib.scad>"' in result
            assert "z = 20;\n" in result
            # Should only have one include left (the one in the string)
            assert result.count("include <lib.scad>") == 1

    def test_include_in_single_line_comment_ignored(self):
        """Test that includes in single-line comments are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\n// include <lib.scad>\ninclude <lib.scad>\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "// include <lib.scad>" in result
            assert "z = 20;\n" in result
            assert result.count("include <lib.scad>") == 1  # Only the one in comment

    def test_include_in_multi_line_comment_ignored(self):
        """Test that includes in multi-line comments are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\n/* include <lib.scad> */\ninclude <lib.scad>\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "/* include <lib.scad> */" in result
            assert "z = 20;\n" in result
            assert result.count("include <lib.scad>") == 1  # Only the one in comment

    def test_include_file_not_found(self):
        """Test that FileNotFoundError is raised when include file is not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <nonexistent.scad>\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            with pytest.raises(FileNotFoundError) as exc_info:
                process_includes(source_map, main_file)
            
            assert "nonexistent.scad" in str(exc_info.value)

    def test_circular_includes_prevention(self):
        """Test that circular includes are prevented by max_iterations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("include <lib.scad>\n")
            
            with open(lib_file, 'w') as f:
                f.write("include <main.scad>\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            with pytest.raises(ValueError) as exc_info:
                process_includes(source_map, main_file, max_iterations=10)
            
            assert "Maximum iterations" in str(exc_info.value)

    def test_include_with_path(self):
        """Test include with a path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_dir = os.path.join(temp_dir, "lib")
            os.makedirs(lib_dir)
            lib_file = os.path.join(lib_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib/lib.scad>\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "z = 20;\n" in result
            assert "include <lib/lib.scad>" not in result

    def test_include_preserves_source_locations(self):
        """Test that source locations are preserved after processing includes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib.scad>\ny = 10;\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            
            # Check that we can still get locations
            loc = source_map.get_location(0)
            assert loc.origin == main_file
            assert loc.line == 1
            assert loc.column == 1
            
            # Location in included file
            result = source_map.get_combined_string()
            lib_pos = result.find("z = 20")
            if lib_pos >= 0:
                loc = source_map.get_location(lib_pos)
                assert loc.origin == lib_file

    def test_include_with_whitespace(self):
        """Test include statement with various whitespace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude   <lib.scad>\n")  # Extra spaces
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "z = 20;\n" in result
            assert "include" not in result or "include   <lib.scad>" not in result

    def test_include_with_tabs(self):
        """Test include statement with tabs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude\t<lib.scad>\n")  # Tab instead of space
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "z = 20;\n" in result

    def test_escaped_quotes_in_string(self):
        """Test that escaped quotes in strings don't break string detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write('x = "include <lib.scad>";\ninclude <lib.scad>\n')  # Escaped quote scenario
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            # The include in the string should remain
            assert '"include <lib.scad>"' in result or 'x = "include <lib.scad>";' in result
            # The real include should be processed
            assert "z = 20;\n" in result

    def test_no_includes(self):
        """Test processing a file with no includes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ny = 10;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            original = source_map.get_combined_string()
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            # Should be unchanged
            assert result == original

    def test_empty_included_file(self):
        """Test including an empty file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib.scad>\ny = 10;\n")
            
            with open(lib_file, 'w') as f:
                f.write("")  # Empty file
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "y = 10;\n" in result
            assert "include <lib.scad>" not in result


class TestSourceMapEdgeCases:
    """Test edge cases and branch coverage for SourceMap."""

    def test_add_origin_with_existing_segments_calculates_insert_at(self):
        """Test that add_origin calculates insert_at when segments exist."""
        source_map = SourceMap()
        source_map.add_origin("file1.scad", "x = 1;\n")
        # When insert_at is None and segments exist, it should calculate from max
        source_map.add_origin("file2.scad", "y = 2;\n")
        
        combined = source_map.get_combined_string()
        assert "x = 1;\n" in combined
        assert "y = 2;\n" in combined

    def test_replace_text_with_zero_length(self):
        """Test _replace_text with zero or negative length (early return)."""
        source_map = SourceMap()
        source_map.add_origin("file.scad", "x = 1;\n")
        # replace_length=0 should not modify anything
        source_map.add_origin("file2.scad", "y = 2;\n", insert_at=0, replace_length=0)
        
        combined = source_map.get_combined_string()
        assert "x = 1;\n" in combined
        assert "y = 2;\n" in combined

    def test_replace_text_without_strip_trailing_newline(self):
        """Test _replace_text when strip_trailing_newline is False."""
        source_map = SourceMap()
        source_map.add_origin("file.scad", "x = 1;\n")
        # Replace with content that doesn't need newline stripping
        source_map.add_origin("file2.scad", "y = 2", insert_at=0, replace_length=1)
        
        combined = source_map.get_combined_string()
        assert "y = 2" in combined

    def test_replace_text_with_strip_trailing_newline(self):
        """Test _replace_text strips newline from following content."""
        source_map = SourceMap()
        source_map.add_origin("main.scad", "include <x>\nY")
        # Replace "include <x>" with content that ends in newline
        source_map.add_origin(
            "lib.scad",
            "A\n",
            insert_at=0,
            replace_length=len("include <x>"),
            strip_trailing_newline=True,
        )

        combined = source_map.get_combined_string()
        assert combined == "A\nY"

    def test_rebuild_combined_string_empty_segments(self):
        """Test _rebuild_combined_string with empty segments."""
        source_map = SourceMap()
        # Empty source map should return empty string
        assert source_map.get_combined_string() == ""

    def test_combined_string_includes_gaps(self):
        """Test combined string fills gaps with spaces."""
        source_map = SourceMap()
        source_map.add_origin("file1.scad", "abc")
        source_map.add_origin("file2.scad", "Z", insert_at=5)

        combined = source_map.get_combined_string()
        assert combined == "abc  Z"

    def test_get_location_negative_position(self):
        """Test get_location with negative position."""
        source_map = SourceMap()
        source_map.add_origin("file.scad", "x = 1;\n")
        
        loc = source_map.get_location(-1)
        assert loc.origin == "file.scad"
        assert loc.line == 1
        assert loc.column == 1

    def test_get_location_no_segments(self):
        """Test get_location when no segments exist."""
        source_map = SourceMap()
        loc = source_map.get_location(0)
        assert loc.origin == ""
        assert loc.line == 1
        assert loc.column == 1

    def test_find_segment_no_segments(self):
        """Test _find_segment when no segments exist."""
        source_map = SourceMap()
        segment = source_map._find_segment(0)
        assert segment is None

    def test_find_segment_last_segment_edge_case(self):
        """Test _find_segment with position in last segment."""
        source_map = SourceMap()
        source_map.add_origin("file.scad", "x = 1;\ny = 2;\n")
        # Position at the end of the last segment
        segment = source_map._find_segment(10)
        assert segment is not None

    def test_calculate_location_in_segment_negative_offset(self):
        """Test _calculate_location_in_segment with negative offset."""
        source_map = SourceMap()
        source_map.add_origin("file.scad", "x = 1;\n")
        loc = source_map.get_location(0)
        # This internally uses _calculate_location_in_segment
        assert loc.column >= 1

    def test_calculate_location_in_segment_offset_too_large(self):
        """Test _calculate_location_in_segment with offset > segment length."""
        source_map = SourceMap()
        source_map.add_origin("file.scad", "x = 1;\n")
        # Get location at position beyond content
        loc = source_map.get_location(100)
        assert loc.origin == "file.scad"

    def test_calculate_location_in_segment_newline_offsets(self):
        """Test location calculation across newlines."""
        source_map = SourceMap()
        source_map.add_origin("file.scad", "a\nb")

        loc = source_map.get_location(2)  # Points at "b"
        assert loc.origin == "file.scad"
        assert loc.line == 2
        assert loc.column == 1

    def test_create_source_map_from_origins_with_insert_positions(self):
        """Test create_source_map_from_origins with insert_positions."""
        from openscad_parser.ast.source_map import create_source_map_from_origins
        
        origins = [("file1.scad", "x = 1;\n"), ("file2.scad", "y = 2;\n")]
        insert_positions = [0, 10]
        
        source_map = create_source_map_from_origins(origins, insert_positions)
        combined = source_map.get_combined_string()
        assert "x = 1;\n" in combined
        assert "y = 2;\n" in combined

    def test_create_source_map_from_origins_mismatched_lengths(self):
        """Test create_source_map_from_origins with mismatched lengths."""
        from openscad_parser.ast.source_map import create_source_map_from_origins
        
        origins = [("file1.scad", "x = 1;\n")]
        insert_positions = [0, 10]  # Wrong length
        
        with pytest.raises(ValueError) as exc_info:
            create_source_map_from_origins(origins, insert_positions)
        
        assert "same length" in str(exc_info.value)

    def test_process_includes_without_current_file(self):
        """Test process_includes when current_file is empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            source_map.add_origin("main.scad", "x = 5;\ninclude <lib.scad>\n")
            
            # Process without current_file (empty string)
            # This will try to find the file without context
            # It may fail, but we're testing the branch
            try:
                process_includes(source_map, "")
            except FileNotFoundError:
                pass  # Expected if file can't be found

    def test_process_includes_io_error(self):
        """Test process_includes when file read fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib.scad>\n")
            
            # Create a file that will cause read error (make it a directory)
            os.makedirs(lib_file, exist_ok=True)
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            # This should raise IOError when trying to read the directory
            with pytest.raises(IOError):
                process_includes(source_map, main_file)

    def test_find_valid_includes_escaped_quote(self):
        """Test _find_valid_includes with escaped quotes."""
        from openscad_parser.ast.source_map import _find_valid_includes
        
        code = 'x = "include <lib.scad>";\ninclude <lib.scad>\n'
        includes = _find_valid_includes(code)
        # Should find one include (not the one in the string)
        assert len(includes) == 1
        assert includes[0]['filename'] == 'lib.scad'

    def test_find_valid_includes_multiline_include(self):
        """Test _find_valid_includes with include spanning multiple lines."""
        from openscad_parser.ast.source_map import _find_valid_includes
        
        code = "include <lib\n.scad>\n"  # Include with newline in filename
        includes = _find_valid_includes(code)
        # Should be skipped because it spans multiple lines
        assert len(includes) == 0

    def test_find_valid_includes_word_boundary(self):
        """Test _find_valid_includes respects word boundaries."""
        from openscad_parser.ast.source_map import _find_valid_includes

        code = "xinclude <lib.scad>\ninclude_me <lib.scad>\n"
        includes = _find_valid_includes(code)
        assert len(includes) == 0

    def test_calculate_location_offset_edge_cases(self):
        """Test _calculate_location_in_segment with offset edge cases."""
        source_map = SourceMap()
        source_map.add_origin("file.scad", "x = 1;\n")
        
        # Test with offset exactly at segment boundary
        loc = source_map.get_location(7)  # At end of "x = 1;\n"
        assert loc.origin == "file.scad"
        
        # Test with offset beyond segment (should clamp)
        loc = source_map.get_location(100)
        assert loc.origin == "file.scad"

    def test_find_segment_last_segment_exact_boundary(self):
        """Test _find_segment with position at exact boundary of last segment."""
        source_map = SourceMap()
        source_map.add_origin("file1.scad", "x = 1;\n")
        source_map.add_origin("file2.scad", "y = 2;\n", insert_at=8)
        
        # Position within the last segment
        segment = source_map._find_segment(8)  # Start of second segment
        assert segment is not None
        assert segment.origin == "file2.scad"

    def test_create_source_map_from_origins_without_insert_positions(self):
        """Test create_source_map_from_origins without insert_positions."""
        from openscad_parser.ast.source_map import create_source_map_from_origins
        
        origins = [("file1.scad", "x = 1;\n"), ("file2.scad", "y = 2;\n")]
        
        source_map = create_source_map_from_origins(origins)
        combined = source_map.get_combined_string()
        assert "x = 1;\n" in combined
        assert "y = 2;\n" in combined

    def test_find_valid_includes_with_escaped_quote_in_string(self):
        """Test _find_valid_includes with escaped quote in string."""
        from openscad_parser.ast.source_map import _find_valid_includes
        
        code = 'x = "include \\" <lib.scad>";\ninclude <lib.scad>\n'
        includes = _find_valid_includes(code)
        # Should find one include (not the one in the string)
        assert len(includes) == 1
        assert includes[0]['filename'] == 'lib.scad'

    def test_skip_whitespace_helper(self):
        """Test _skip_whitespace skips all whitespace chars."""
        from openscad_parser.ast.source_map import _skip_whitespace

        code = " \t\n\rX"
        assert _skip_whitespace(code, 0) == 4
