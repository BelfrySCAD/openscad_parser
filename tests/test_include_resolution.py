"""include<> resolution as OpenSCAD 2026.02.01 does it: each case's statements
match the ECHOs the reference prints for the same files."""
import os

from openscad_parser.ast import getASTfromFile


def _files(tmp_path, **files):
    for name, text in files.items():
        (tmp_path / f"{name}.scad").write_text(text)


def _echoes(path):
    return [str(n).strip() for n in getASTfromFile(str(path))]


def test_a_file_included_twice_is_included_twice(tmp_path):
    _files(tmp_path, lib='echo("lib");\n', main="include <lib.scad>\ninclude <lib.scad>\n")
    assert _echoes(tmp_path / "main.scad") == ['echo("lib")', 'echo("lib")']


def test_a_file_reached_by_two_paths_is_included_by_both(tmp_path):
    _files(tmp_path, lib='echo("lib");\n', mid='echo("mid");\ninclude <lib.scad>\n',
           main="include <lib.scad>\ninclude <mid.scad>\n")
    assert _echoes(tmp_path / "main.scad") == ['echo("lib")', 'echo("mid")', 'echo("lib")']


def test_only_a_file_open_on_the_chain_is_refused(tmp_path):
    # OpenSCAD opens the top file again once (it is not on the include chain),
    # then warns it can't find a file that is.
    _files(tmp_path, me='echo("me");\ninclude <me.scad>\n',
           a='echo("a");\ninclude <b.scad>\n', b='echo("b");\ninclude <a.scad>\n')
    assert _echoes(tmp_path / "me.scad") == ['echo("me")', 'echo("me")']
    assert _echoes(tmp_path / "a.scad") == ['echo("a")', 'echo("b")', 'echo("a")']


def test_editing_an_included_file_is_noticed(tmp_path):
    _files(tmp_path, lib='echo("old");\n', main="include <lib.scad>\n")
    main = tmp_path / "main.scad"
    assert _echoes(main) == ['echo("old")']
    lib = tmp_path / "lib.scad"
    lib.write_text('echo("new");\necho("more");\n')
    st = os.stat(lib)
    os.utime(lib, (st.st_atime, st.st_mtime + 5))  # the top file is untouched
    assert _echoes(main) == ['echo("new")', 'echo("more")']
