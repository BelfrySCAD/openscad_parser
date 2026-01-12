#######################################################################
# Arpeggio PEG Grammar for OpenSCAD
#######################################################################

from __future__ import unicode_literals

from arpeggio import ParserPython
from .grammar import openscad_language, openscad_language_with_comments, comment, whitespace_only


# --- The parser ---

def getOpenSCADParser(reduce_tree=False, debug=False, include_comments=False):
    """Create an OpenSCAD parser instance.
    
    Args:
        reduce_tree: If True, reduce the parse tree (default: False)
        debug: If True, enable debug output (default: False)
        include_comments: If True, include comments in the AST instead of skipping them (default: False)
    
    Returns:
        ParserPython instance configured for OpenSCAD parsing
    """
    if include_comments:
        # When including comments, use whitespace-only rule and include comments in grammar
        return ParserPython(
            openscad_language_with_comments, whitespace_only, reduce_tree=reduce_tree,
            memoization=True, autokwd=True, debug=debug
        )
    else:
        # Default behavior: comments are skipped as whitespace
        return ParserPython(
            openscad_language, comment, reduce_tree=reduce_tree,
            memoization=True, autokwd=True, debug=debug
        )


# vim: set ts=4 sw=4 expandtab:
