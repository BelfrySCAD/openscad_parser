"""Tests for the openscad-parser CLI."""

import io
import json
import subprocess
import sys
import pytest


def _run(*args, stdin=None):
    """Run openscad-parser via the module entry point and return (stdout, stderr, returncode)."""
    cmd = [sys.executable, "-m", "openscad_parser.cli"] + list(args)
    result = subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
    )
    return result.stdout, result.stderr, result.returncode


class TestCLIJsonOutput:
    def test_stdin_json(self):
        out, err, rc = _run("-", stdin="x = 42;")
        assert rc == 0
        data = json.loads(out)
        assert isinstance(data, list)
        assert data[0]["_type"] == "Assignment"

    def test_explicit_json_flag(self):
        out, err, rc = _run("--json", "-", stdin="cube(10);")
        assert rc == 0
        data = json.loads(out)
        assert data[0]["_type"] == "ModularCall"

    def test_json_indent(self):
        out, err, rc = _run("--indent", "2", "-", stdin="x = 1;")
        assert rc == 0
        # 2-space indent: second line starts with 2 spaces
        lines = out.splitlines()
        assert any(l.startswith("  ") and not l.startswith("   ") for l in lines)

    def test_file_input(self, tmp_path):
        f = tmp_path / "test.scad"
        f.write_text("width = 20;\ncube([width, 10, 5]);")
        out, err, rc = _run(str(f))
        assert rc == 0
        data = json.loads(out)
        assert len(data) == 2
        assert data[0]["_type"] == "Assignment"
        assert data[1]["_type"] == "ModularCall"


class TestCLIYamlOutput:
    def test_yaml_output(self):
        out, err, rc = _run("--yaml", "-", stdin="x = 1;")
        assert rc == 0
        assert "_type: Assignment" in out

    def test_yaml_multiple_nodes(self):
        out, err, rc = _run("--yaml", "-", stdin="x = 1;\ny = 2;")
        assert rc == 0
        assert out.count("_type: Assignment") == 2


class TestCLIFormatOutput:
    def test_format_assignment(self):
        out, err, rc = _run("--format", "-", stdin="x=42;")
        assert rc == 0
        assert out.strip() == "x = 42;"

    def test_format_module(self):
        out, err, rc = _run("--format", "-", stdin="module m(x){cube(x);}")
        assert rc == 0
        assert "module m(x)" in out
        assert "cube(x);" in out

    def test_format_indent(self):
        out, err, rc = _run("--format", "--indent", "2", "-", stdin="module m(){cube(1);}")
        assert rc == 0
        assert "  cube(1);" in out

    def test_format_file(self, tmp_path):
        f = tmp_path / "model.scad"
        f.write_text("module box(w,h){cube([w,h,1]);}")
        out, err, rc = _run("--format", str(f))
        assert rc == 0
        assert "module box(w, h)" in out


class TestCLIOptions:
    def test_include_comments(self):
        out, err, rc = _run("--json", "--include-comments", "-", stdin="// hi\nx=1;")
        assert rc == 0
        data = json.loads(out)
        types = [n["_type"] for n in data]
        assert "CommentLine" in types

    def test_no_includes(self, tmp_path):
        f = tmp_path / "test.scad"
        f.write_text("include <missing.scad>\nx = 1;")
        out, err, rc = _run("--no-includes", str(f))
        assert rc == 0
        data = json.loads(out)
        types = [n["_type"] for n in data]
        assert "IncludeStatement" in types


class TestCLIErrors:
    def test_missing_file(self):
        out, err, rc = _run("/no/such/file.scad")
        assert rc != 0
        assert "openscad-parser" in err

    def test_syntax_error_exits_nonzero(self):
        out, err, rc = _run("-", stdin="invalid @@@ syntax")
        assert rc != 0


# ---------------------------------------------------------------------------
# In-process tests: call main() directly so coverage is tracked
# ---------------------------------------------------------------------------

from openscad_parser.cli import main


class TestCLIMainInProcess:
    def test_stdin_json(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "-"])
        monkeypatch.setattr(sys, "stdin", io.StringIO("x = 42;"))
        main()
        out, _ = capsys.readouterr()
        data = json.loads(out)
        assert data[0]["_type"] == "Assignment"

    def test_explicit_json_flag(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "--json", "-"])
        monkeypatch.setattr(sys, "stdin", io.StringIO("cube(10);"))
        main()
        out, _ = capsys.readouterr()
        assert json.loads(out)[0]["_type"] == "ModularCall"

    def test_json_indent(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "--indent", "2", "-"])
        monkeypatch.setattr(sys, "stdin", io.StringIO("x = 1;"))
        main()
        out, _ = capsys.readouterr()
        lines = out.splitlines()
        assert any(l.startswith("  ") and not l.startswith("   ") for l in lines)

    def test_file_input(self, monkeypatch, capsys, tmp_path):
        f = tmp_path / "test.scad"
        f.write_text("width = 20;\ncube([width, 10, 5]);")
        monkeypatch.setattr(sys, "argv", ["openscad-parser", str(f)])
        main()
        out, _ = capsys.readouterr()
        data = json.loads(out)
        assert len(data) == 2

    def test_format_flag(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "--format", "-"])
        monkeypatch.setattr(sys, "stdin", io.StringIO("cube(10);"))
        main()
        out, _ = capsys.readouterr()
        assert "cube(10);" in out

    def test_format_indent(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "--format", "--indent", "2", "-"])
        monkeypatch.setattr(sys, "stdin", io.StringIO("module m(){cube(1);}"))
        main()
        out, _ = capsys.readouterr()
        assert "  cube(1);" in out

    def test_yaml_flag(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "--yaml", "-"])
        monkeypatch.setattr(sys, "stdin", io.StringIO("x = 1;"))
        main()
        out, _ = capsys.readouterr()
        assert "_type: Assignment" in out

    def test_include_comments(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "--include-comments", "-"])
        monkeypatch.setattr(sys, "stdin", io.StringIO("// hi\nx=1;"))
        main()
        out, _ = capsys.readouterr()
        data = json.loads(out)
        types = [n["_type"] for n in data]
        assert "CommentLine" in types

    def test_no_includes(self, monkeypatch, capsys, tmp_path):
        f = tmp_path / "test.scad"
        f.write_text("include <missing.scad>\nx = 1;")
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "--no-includes", str(f)])
        main()
        out, _ = capsys.readouterr()
        data = json.loads(out)
        types = [n["_type"] for n in data]
        assert "IncludeStatement" in types

    def test_missing_file(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "/no/such/file.scad"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        _, err = capsys.readouterr()
        assert "openscad-parser" in err

    def test_syntax_error_exits_nonzero(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["openscad-parser", "-"])
        monkeypatch.setattr(sys, "stdin", io.StringIO("invalid @@@ syntax"))
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
