"""JSON and YAML serialization for OpenSCAD AST trees.

This module provides functions to serialize AST trees to JSON and YAML formats,
and to deserialize them back to AST nodes.

Example:
    from openscad_parser.ast import getASTfromString, ast_to_json, ast_from_json

    ast = getASTfromString("cube(10);")
    json_str = ast_to_json(ast)
    ast_restored = ast_from_json(json_str)
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from .builder import Position
from .nodes import (
    ASTNode,
    CommentLine,
    CommentSpan,
    Expression,
    Primary,
    Identifier,
    StringLiteral,
    NumberLiteral,
    BooleanLiteral,
    UndefinedLiteral,
    ParameterDeclaration,
    Argument,
    PositionalArgument,
    NamedArgument,
    RangeLiteral,
    Assignment,
    LetOp,
    EchoOp,
    AssertOp,
    UnaryMinusOp,
    AdditionOp,
    SubtractionOp,
    MultiplicationOp,
    DivisionOp,
    ModuloOp,
    ExponentOp,
    BitwiseAndOp,
    BitwiseOrOp,
    BitwiseNotOp,
    BitwiseShiftLeftOp,
    BitwiseShiftRightOp,
    LogicalAndOp,
    LogicalOrOp,
    LogicalNotOp,
    TernaryOp,
    EqualityOp,
    InequalityOp,
    GreaterThanOp,
    GreaterThanOrEqualOp,
    LessThanOp,
    LessThanOrEqualOp,
    FunctionLiteral,
    PrimaryCall,
    PrimaryIndex,
    PrimaryMember,
    VectorElement,
    ListCompLet,
    ListCompEach,
    ListCompFor,
    ListCompCFor,
    ListCompIf,
    ListCompIfElse,
    ListComprehension,
    ModuleInstantiation,
    ModularCall,
    ModularFor,
    ModularCFor,
    ModularIntersectionFor,
    ModularIntersectionCFor,
    ModularLet,
    ModularEcho,
    ModularAssert,
    ModularIf,
    ModularIfElse,
    ModularModifierShowOnly,
    ModularModifierHighlight,
    ModularModifierBackground,
    ModularModifierDisable,
    ModuleDeclaration,
    FunctionDeclaration,
    UseStatement,
    IncludeStatement,
)


# Registry mapping class names to classes for deserialization
_NODE_REGISTRY: dict[str, type[ASTNode]] = {
    cls.__name__: cls
    for cls in [
        # Comments
        CommentLine,
        CommentSpan,
        # Literals/Primaries
        Identifier,
        StringLiteral,
        NumberLiteral,
        BooleanLiteral,
        UndefinedLiteral,
        RangeLiteral,
        # Parameters and Arguments
        ParameterDeclaration,
        PositionalArgument,
        NamedArgument,
        # Assignments
        Assignment,
        # Expression operators
        LetOp,
        EchoOp,
        AssertOp,
        UnaryMinusOp,
        AdditionOp,
        SubtractionOp,
        MultiplicationOp,
        DivisionOp,
        ModuloOp,
        ExponentOp,
        BitwiseAndOp,
        BitwiseOrOp,
        BitwiseNotOp,
        BitwiseShiftLeftOp,
        BitwiseShiftRightOp,
        LogicalAndOp,
        LogicalOrOp,
        LogicalNotOp,
        TernaryOp,
        EqualityOp,
        InequalityOp,
        GreaterThanOp,
        GreaterThanOrEqualOp,
        LessThanOp,
        LessThanOrEqualOp,
        # Function/Call expressions
        FunctionLiteral,
        PrimaryCall,
        PrimaryIndex,
        PrimaryMember,
        # List comprehension
        ListCompLet,
        ListCompEach,
        ListCompFor,
        ListCompCFor,
        ListCompIf,
        ListCompIfElse,
        ListComprehension,
        # Module instantiations
        ModularCall,
        ModularFor,
        ModularCFor,
        ModularIntersectionFor,
        ModularIntersectionCFor,
        ModularLet,
        ModularEcho,
        ModularAssert,
        ModularIf,
        ModularIfElse,
        ModularModifierShowOnly,
        ModularModifierHighlight,
        ModularModifierBackground,
        ModularModifierDisable,
        # Declarations
        ModuleDeclaration,
        FunctionDeclaration,
        UseStatement,
        IncludeStatement,
    ]
}


def _serialize_position(position: Position) -> dict[str, Any]:
    """Serialize a Position to a dictionary."""
    return {
        "origin": position.origin,
        "line": position.line,
        "column": position.column,
    }


def _serialize_value(value: Any, include_position: bool) -> Any:
    """Serialize a field value recursively."""
    if value is None:
        return None
    elif isinstance(value, ASTNode):
        return _serialize_node(value, include_position)
    elif isinstance(value, list):
        return [_serialize_value(item, include_position) for item in value]
    elif isinstance(value, (str, int, float, bool)):
        return value
    else:
        raise TypeError(f"Unsupported type for serialization: {type(value)}")


def _serialize_node(node: ASTNode, include_position: bool) -> dict[str, Any]:
    """Serialize a single AST node to a dictionary."""
    result: dict[str, Any] = {
        "_type": node.__class__.__name__,
    }

    if include_position:
        result["_position"] = _serialize_position(node.position)

    # Get all fields from the dataclass (excluding 'position' which we handle specially)
    for field in dataclasses.fields(node):
        if field.name == "position":
            continue
        value = getattr(node, field.name)
        result[field.name] = _serialize_value(value, include_position)

    return result


def ast_to_dict(
    ast: ASTNode | list[ASTNode] | None,
    include_position: bool = True,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Convert an AST to a Python dictionary (JSON-serializable).

    Args:
        ast: An AST node, list of AST nodes, or None.
        include_position: If True, include source position information (default: True).

    Returns:
        A dictionary representation of the AST, a list of dictionaries, or None.

    Example:
        ast = getASTfromString("x = 42;")
        data = ast_to_dict(ast)
    """
    if ast is None:
        return None
    elif isinstance(ast, list):
        return [_serialize_node(node, include_position) for node in ast]
    else:
        return _serialize_node(ast, include_position)


def ast_to_json(
    ast: ASTNode | list[ASTNode] | None,
    include_position: bool = True,
    indent: int | None = 2,
) -> str:
    """Serialize an AST to a JSON string.

    Args:
        ast: An AST node, list of AST nodes, or None.
        include_position: If True, include source position information (default: True).
        indent: Indentation level for pretty-printing. Use None for compact output.

    Returns:
        A JSON string representation of the AST.

    Example:
        ast = getASTfromString("cube(10);")
        json_str = ast_to_json(ast)
    """
    data = ast_to_dict(ast, include_position=include_position)
    return json.dumps(data, indent=indent)


def _deserialize_position(data: dict[str, Any]) -> Position:
    """Deserialize a Position from a dictionary."""
    return Position(
        origin=data["origin"],
        line=data["line"],
        column=data["column"],
    )


def _deserialize_value(value: Any) -> Any:
    """Deserialize a field value recursively."""
    if value is None:
        return None
    elif isinstance(value, dict) and "_type" in value:
        return _deserialize_node(value)
    elif isinstance(value, list):
        return [_deserialize_value(item) for item in value]
    elif isinstance(value, (str, int, float, bool)):
        return value
    else:
        raise TypeError(f"Unsupported type for deserialization: {type(value)}")


def _deserialize_node(data: dict[str, Any]) -> ASTNode:
    """Deserialize a single AST node from a dictionary."""
    if "_type" not in data:
        raise ValueError("Missing '_type' field in node data")

    type_name = data["_type"]
    if type_name not in _NODE_REGISTRY:
        raise ValueError(f"Unknown node type: {type_name}")

    node_class = _NODE_REGISTRY[type_name]

    # Reconstruct position (required for all nodes)
    if "_position" in data:
        position = _deserialize_position(data["_position"])
    else:
        # Default position if not provided
        position = Position(origin="<unknown>", line=0, column=0)

    # Get field names from dataclass (excluding position)
    field_names = {f.name for f in dataclasses.fields(node_class) if f.name != "position"}

    # Build kwargs for constructor
    kwargs: dict[str, Any] = {"position": position}
    for key, value in data.items():
        if key.startswith("_"):
            continue  # Skip _type, _position
        if key in field_names:
            kwargs[key] = _deserialize_value(value)

    return node_class(**kwargs)


def ast_from_dict(data: dict[str, Any] | list[dict[str, Any]] | None) -> ASTNode | list[ASTNode] | None:
    """Reconstruct an AST from a Python dictionary.

    Args:
        data: A dictionary, list of dictionaries, or None (as returned by ast_to_dict).

    Returns:
        An AST node, list of AST nodes, or None.

    Raises:
        ValueError: If the data contains an unknown node type or is malformed.

    Example:
        data = ast_to_dict(ast)
        ast_restored = ast_from_dict(data)
    """
    if data is None:
        return None
    elif isinstance(data, list):
        return [_deserialize_node(item) for item in data]
    else:
        return _deserialize_node(data)


def ast_from_json(json_str: str) -> ASTNode | list[ASTNode] | None:
    """Deserialize an AST from a JSON string.

    Args:
        json_str: A JSON string (as returned by ast_to_json).

    Returns:
        An AST node, list of AST nodes, or None.

    Raises:
        ValueError: If the JSON contains an unknown node type or is malformed.
        json.JSONDecodeError: If the string is not valid JSON.

    Example:
        json_str = ast_to_json(ast)
        ast_restored = ast_from_json(json_str)
    """
    data = json.loads(json_str)
    return ast_from_dict(data)


def ast_to_yaml(
    ast: ASTNode | list[ASTNode] | None,
    include_position: bool = True,
) -> str:
    """Serialize an AST to a YAML string.

    Requires PyYAML to be installed: pip install openscad_parser[yaml]

    Args:
        ast: An AST node, list of AST nodes, or None.
        include_position: If True, include source position information (default: True).

    Returns:
        A YAML string representation of the AST.

    Raises:
        ImportError: If PyYAML is not installed.

    Example:
        ast = getASTfromString("cube(10);")
        yaml_str = ast_to_yaml(ast)
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for YAML serialization. "
            "Install it with: pip install openscad_parser[yaml]"
        )

    data = ast_to_dict(ast, include_position=include_position)
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def ast_from_yaml(yaml_str: str) -> ASTNode | list[ASTNode] | None:
    """Deserialize an AST from a YAML string.

    Requires PyYAML to be installed: pip install openscad_parser[yaml]

    Args:
        yaml_str: A YAML string (as returned by ast_to_yaml).

    Returns:
        An AST node, list of AST nodes, or None.

    Raises:
        ImportError: If PyYAML is not installed.
        ValueError: If the YAML contains an unknown node type or is malformed.

    Example:
        yaml_str = ast_to_yaml(ast)
        ast_restored = ast_from_yaml(yaml_str)
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for YAML deserialization. "
            "Install it with: pip install openscad_parser[yaml]"
        )

    data = yaml.safe_load(yaml_str)
    return ast_from_dict(data)
