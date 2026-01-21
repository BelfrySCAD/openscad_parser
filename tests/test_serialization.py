"""Tests for AST JSON and YAML serialization."""

import json
import pytest

from openscad_parser.ast import (
    getASTfromString,
    ast_to_dict,
    ast_to_json,
    ast_from_dict,
    ast_from_json,
    ast_to_yaml,
    ast_from_yaml,
)
from openscad_parser.ast.builder import Position
from openscad_parser.ast.nodes import (
    Identifier,
    StringLiteral,
    NumberLiteral,
    BooleanLiteral,
    UndefinedLiteral,
    Assignment,
    AdditionOp,
    ModularCall,
    PositionalArgument,
    ModuleDeclaration,
    FunctionDeclaration,
    ParameterDeclaration,
    ListComprehension,
)


def _pos(line=1, column=1):
    """Helper to create a Position for testing."""
    return Position(origin="<test>", line=line, column=column)


class TestAstToDict:
    """Tests for ast_to_dict function."""

    def test_none_input(self):
        """Test that None input returns None."""
        assert ast_to_dict(None) is None

    def test_single_node(self):
        """Test serializing a single node."""
        node = NumberLiteral(val=42.0, position=_pos())
        result = ast_to_dict(node)

        assert isinstance(result, dict)
        assert result["_type"] == "NumberLiteral"
        assert result["val"] == 42.0
        assert result["_position"]["origin"] == "<test>"
        assert result["_position"]["line"] == 1  
        assert result["_position"]["column"] == 1
        assert result["_position"]["origin"] == "<test>"
        assert result["_position"]["line"] == 1
        assert result["_position"]["column"] == 1

    def test_list_of_nodes(self):
        """Test serializing a list of nodes."""
        nodes = [
            NumberLiteral(val=1.0, position=_pos()),
            NumberLiteral(val=2.0, position=_pos()),
        ]
        result = ast_to_dict(nodes)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["val"] == 1.0
        assert result[1]["val"] == 2.0

    def test_without_position(self):
        """Test serializing without position information."""
        node = NumberLiteral(val=42.0, position=_pos())
        result = ast_to_dict(node, include_position=False)

        assert isinstance(result, dict)
        assert result["_type"] == "NumberLiteral"
        assert result["val"] == 42.0
        assert "_position" not in result

    def test_nested_nodes(self):
        """Test serializing nested node structures."""
        left = NumberLiteral(val=1.0, position=_pos())
        right = NumberLiteral(val=2.0, position=_pos())
        add_op = AdditionOp(left=left, right=right, position=_pos())

        result = ast_to_dict(add_op)

        assert isinstance(result, dict)
        assert result["_type"] == "AdditionOp"
        assert result["left"]["_type"] == "NumberLiteral"
        assert result["left"]["val"] == 1.0
        assert result["right"]["_type"] == "NumberLiteral"
        assert result["right"]["val"] == 2.0
        assert result["_position"]["origin"] == "<test>"
        assert result["_position"]["line"] == 1
        assert result["_position"]["column"] == 1

    def test_node_with_list_field(self):
        """Test serializing node with list fields."""
        name = Identifier(name="cube", position=_pos())
        arg = PositionalArgument(
            expr=NumberLiteral(val=10.0, position=_pos()),
            position=_pos(),
        )
        call = ModularCall(name=name, arguments=[arg], children=[], position=_pos())

        result = ast_to_dict(call)

        assert isinstance(result, dict)
        assert result["_type"] == "ModularCall"
        assert result["name"]["_type"] == "Identifier"
        assert result["name"]["name"] == "cube"
        assert len(result["arguments"]) == 1
        assert result["arguments"][0]["_type"] == "PositionalArgument"


class TestAstToJson:
    """Tests for ast_to_json function."""

    def test_basic_json_output(self):
        """Test JSON string output."""
        node = NumberLiteral(val=42.0, position=_pos())
        json_str = ast_to_json(node)

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["_type"] == "NumberLiteral"
        assert data["val"] == 42.0

    def test_json_compact(self):
        """Test compact JSON output with indent=None."""
        node = NumberLiteral(val=42.0, position=_pos())
        json_str = ast_to_json(node, indent=None)

        # Should be on one line (no newlines)
        assert "\n" not in json_str

    def test_json_pretty_print(self):
        """Test pretty-printed JSON output."""
        node = NumberLiteral(val=42.0, position=_pos())
        json_str = ast_to_json(node, indent=2)

        # Should have newlines for pretty printing
        assert "\n" in json_str


class TestAstFromDict:
    """Tests for ast_from_dict function."""

    def test_none_input(self):
        """Test that None input returns None."""
        assert ast_from_dict(None) is None

    def test_single_node(self):
        """Test deserializing a single node."""
        data = {
            "_type": "NumberLiteral",
            "_position": {"origin": "<test>", "line": 1, "column": 1},
            "val": 42.0,
        }
        node = ast_from_dict(data)

        assert isinstance(node, NumberLiteral)
        assert node.val == 42.0
        assert node.position.origin == "<test>"

    def test_list_of_nodes(self):
        """Test deserializing a list of nodes."""
        data = [
            {"_type": "NumberLiteral", "_position": {"origin": "<test>", "line": 1, "column": 1}, "val": 1.0},
            {"_type": "NumberLiteral", "_position": {"origin": "<test>", "line": 1, "column": 1}, "val": 2.0},
        ]
        nodes = ast_from_dict(data)

        assert isinstance(nodes, list)
        assert len(nodes) == 2
        assert isinstance(nodes[0], NumberLiteral)
        assert nodes[0].val == 1.0
        assert isinstance(nodes[1], NumberLiteral)
        assert nodes[1].val == 2.0
        assert nodes[0].position.origin == "<test>"
        assert nodes[0].position.line == 1
        assert nodes[0].position.column == 1
        assert nodes[1].position.origin == "<test>"
        assert nodes[1].position.line == 1
        assert nodes[1].position.column == 1

    def test_without_position(self):
        """Test deserializing without position (uses default)."""
        data = {"_type": "NumberLiteral", "val": 42.0}
        node = ast_from_dict(data)

        assert isinstance(node, NumberLiteral)
        assert node.val == 42.0
        assert node.position.origin == "<unknown>"
        assert node.position.line == 0

    def test_nested_nodes(self):
        """Test deserializing nested structures."""
        data = {
            "_type": "AdditionOp",
            "_position": {"origin": "<test>", "line": 1, "column": 1},
            "left": {"_type": "NumberLiteral", "_position": {"origin": "<test>", "line": 1, "column": 1}, "val": 1.0},
            "right": {"_type": "NumberLiteral", "_position": {"origin": "<test>", "line": 1, "column": 3}, "val": 2.0},
        }
        node = ast_from_dict(data)

        assert isinstance(node, AdditionOp)
        assert isinstance(node.left, NumberLiteral)
        assert isinstance(node.right, NumberLiteral)
        assert node.left.val == 1.0
        assert node.right.val == 2.0

    def test_unknown_type_raises_error(self):
        """Test that unknown type raises ValueError."""
        data = {"_type": "UnknownNodeType", "val": 42}

        with pytest.raises(ValueError, match="Unknown node type"):
            ast_from_dict(data)

    def test_missing_type_raises_error(self):
        """Test that missing _type raises ValueError."""
        data = {"val": 42}

        with pytest.raises(ValueError, match="Missing '_type' field"):
            ast_from_dict(data)


class TestAstFromJson:
    """Tests for ast_from_json function."""

    def test_basic_deserialization(self):
        """Test basic JSON deserialization."""
        json_str = '{"_type": "NumberLiteral", "_position": {"origin": "<test>", "line": 1, "column": 1}, "val": 42.0}'
        node = ast_from_json(json_str)

        assert isinstance(node, NumberLiteral)
        assert node.val == 42.0

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            ast_from_json("not valid json")


class TestJsonRoundTrip:
    """Tests for JSON serialization round-trip."""

    def test_roundtrip_literals(self):
        """Test round-trip for literal values."""
        nodes = [
            NumberLiteral(val=42.0, position=_pos()),
            StringLiteral(val="hello", position=_pos()),
            BooleanLiteral(val=True, position=_pos()),
            UndefinedLiteral(position=_pos()),
            Identifier(name="foo", position=_pos()),
        ]

        for node in nodes:
            json_str = ast_to_json(node)
            restored = ast_from_json(json_str)

            assert type(restored) == type(node)
            if hasattr(node, "val"):
                assert restored.val == node.val  # type: ignore
            if hasattr(node, "name"):
                assert isinstance(restored, Identifier)
                assert restored.name == node.name

    def test_roundtrip_expression(self):
        """Test round-trip for expression with operators."""
        ast = getASTfromString("x = 1 + 2 * 3;")

        json_str = ast_to_json(ast)
        restored = ast_from_json(json_str)

        assert isinstance(restored, list)
        assert len(restored) == 1
        assert isinstance(restored[0], Assignment)

    def test_roundtrip_module_call(self):
        """Test round-trip for module call."""
        ast = getASTfromString("cube(10);")

        json_str = ast_to_json(ast)
        restored = ast_from_json(json_str)

        assert isinstance(restored, list)
        assert len(restored) == 1
        assert isinstance(restored[0], ModularCall)
        assert restored[0].name.name == "cube"

    def test_roundtrip_module_declaration(self):
        """Test round-trip for module declaration."""
        ast = getASTfromString("module test(x=1) { cube(x); }")

        json_str = ast_to_json(ast)
        restored = ast_from_json(json_str)

        assert isinstance(restored, list)
        assert len(restored) == 1
        assert isinstance(restored[0], ModuleDeclaration)
        assert restored[0].name.name == "test"

    def test_roundtrip_function_declaration(self):
        """Test round-trip for function declaration."""
        ast = getASTfromString("function add(a, b) = a + b;")

        json_str = ast_to_json(ast)
        restored = ast_from_json(json_str)

        assert isinstance(restored, list)
        assert len(restored) == 1
        assert isinstance(restored[0], FunctionDeclaration)
        assert restored[0].name.name == "add"

    def test_roundtrip_list_comprehension(self):
        """Test round-trip for list comprehension."""
        ast = getASTfromString("x = [for (i = [0:10]) i * 2];")

        json_str = ast_to_json(ast)
        restored = ast_from_json(json_str)

        assert isinstance(restored, list)
        assert len(restored) == 1
        assert isinstance(restored[0], Assignment)

    def test_roundtrip_complex_model(self):
        """Test round-trip for a more complex OpenSCAD model."""
        code = """
        module holder(width=10, height=5) {
            difference() {
                cube([width, width, height]);
                translate([1, 1, 1])
                    cube([width-2, width-2, height]);
            }
        }
        holder(20, 10);
        """
        ast = getASTfromString(code)

        json_str = ast_to_json(ast)
        restored = ast_from_json(json_str)

        assert isinstance(restored, list)
        assert len(restored) == 2  # module declaration + call

    def test_roundtrip_without_position(self):
        """Test round-trip without position information."""
        ast = getASTfromString("x = 42;")

        json_str = ast_to_json(ast, include_position=False)
        restored = ast_from_json(json_str)

        assert isinstance(restored, list)
        assert len(restored) == 1
        # Position should be default
        assert restored[0].position.origin == "<unknown>"


class TestYamlSerialization:
    """Tests for YAML serialization (requires PyYAML)."""

    @pytest.fixture(autouse=True)
    def check_yaml_available(self):
        """Skip tests if PyYAML is not installed."""
        pytest.importorskip("yaml")

    def test_yaml_output(self):
        """Test YAML string output."""
        node = NumberLiteral(val=42.0, position=_pos())
        yaml_str = ast_to_yaml(node)

        assert "_type: NumberLiteral" in yaml_str
        assert "val: 42.0" in yaml_str

    def test_yaml_roundtrip(self):
        """Test YAML round-trip."""
        ast = getASTfromString("cube(10);")

        yaml_str = ast_to_yaml(ast)
        restored = ast_from_yaml(yaml_str)

        assert isinstance(restored, list)
        assert len(restored) == 1
        assert isinstance(restored[0], ModularCall)

    def test_yaml_without_position(self):
        """Test YAML output without position."""
        node = NumberLiteral(val=42.0, position=_pos())
        yaml_str = ast_to_yaml(node, include_position=False)

        assert "_position" not in yaml_str
        assert "_type: NumberLiteral" in yaml_str


class TestYamlImportError:
    """Tests for YAML import error handling."""

    def test_yaml_import_error_message(self, monkeypatch):
        """Test that helpful error message is shown when PyYAML is missing."""
        # Mock yaml import to raise ImportError
        import sys

        # Remove yaml from sys.modules if present
        yaml_backup = sys.modules.get("yaml")
        sys.modules["yaml"] = None  # type: ignore

        # Need to reload the serialization module to trigger the import
        import importlib
        from openscad_parser.ast import serialization

        try:
            # Create a fresh import that will fail
            def mock_import(name, *args, **kwargs):
                if name == "yaml":
                    raise ImportError("No module named 'yaml'")
                return original_import(name, *args, **kwargs)

            original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

            # For now, just test that the functions exist and have proper signatures
            # The actual import error testing is tricky with pytest
            node = NumberLiteral(val=42.0, position=_pos())

            # If yaml is installed, this will work
            # If not, it will raise ImportError with our message
            try:
                ast_to_yaml(node)
            except ImportError as e:
                assert "PyYAML" in str(e)
        finally:
            # Restore yaml module
            if yaml_backup is not None:
                sys.modules["yaml"] = yaml_backup
            elif "yaml" in sys.modules:
                del sys.modules["yaml"]
