import os
import platform
from dataclasses import dataclass
from typing import Optional
from arpeggio import PTNodeVisitor
from openscad_parser import getOpenSCADParser


@dataclass
class Position:
    """Represents a position in source code.
    
    Stores only the character position and input string. Line and column are
    calculated lazily when accessed via the line and char properties.
    """
    file: str
    position: int  # Character position (0-indexed)
    input_str: str = ""  # Input string for lazy line/column calculation
    
    def _calculate_line_col(self) -> tuple[int, int]:
        """Calculate (line, column) tuple from character position.
        
        Returns:
            Tuple of (line_number, column_number), both 1-indexed
        """
        if not self.input_str or self.position < 0 or self.position > len(self.input_str):
            return (1, 1)
        
        # Count newlines before this position
        text_before = self.input_str[:self.position]
        line_number = text_before.count('\n') + 1
        
        # Find the column (character position on the current line)
        last_newline = text_before.rfind('\n')
        column_number = self.position - last_newline  # 1-indexed
        
        return (line_number, column_number)
    
    @property
    def line(self) -> int:
        """Get the line number (1-indexed) for this position (lazy evaluation)."""
        return self._calculate_line_col()[0]
    
    @property
    def char(self) -> int:
        """Get the column number (1-indexed) for this position (lazy evaluation)."""
        return self._calculate_line_col()[1]


@dataclass
class ASTNode(object):
    """Base class for all AST nodes.
    
    All AST nodes in the OpenSCAD parser inherit from this class. It provides
    a common interface for source position tracking and string representation.
    
    Attributes:
        position: The source position of this node in the original OpenSCAD code.
    """
    position: Position

    def __str__(self) -> str:
        """Return a string representation of the AST node."""
        raise NotImplementedError


@dataclass
class CommentLine(ASTNode):
    """Represents a single-line OpenSCAD comment.
    
    Single-line comments in OpenSCAD start with // and continue to the end of the line.
    
    Example:
        // This is a comment
        x = 1; // This is also a comment
    
    Attributes:
        text: The comment text without the leading // marker.
    """
    text: str

    def __str__(self):
        return f"//{self.text}"


@dataclass
class CommentSpan(ASTNode):
    """Represents a multi-line OpenSCAD comment span.
    
    Multi-line comments in OpenSCAD are enclosed between /* and */.
    
    Example:
        /* This is a
           multi-line comment */
    
    Attributes:
        text: The comment text without the /* and */ markers.
    """
    text: str

    def __str__(self):
        return f"/*{self.text}*/"


@dataclass
class Expression(ASTNode):
    """Base class for all OpenSCAD expressions.
    
    Expressions are constructs that evaluate to a value. This includes:
    - Literals (numbers, strings, booleans)
    - Operators (arithmetic, logical, comparison, etc.)
    - Function calls
    - Variable references
    - Complex expressions combining the above
    
    All expression nodes in the AST inherit from this class.
    """
    pass


@dataclass
class Primary(Expression):
    """Base class for all OpenSCAD primary (atomic) value types.
    
    Primary expressions are the most basic expressions that cannot be further
    decomposed. This includes literals and identifiers.
    
    Examples:
        - Number literals: 42, 3.14, 1e10
        - String literals: "hello", 'world'
        - Boolean literals: true, false
        - Undefined: undef
        - Identifiers: foo, bar, myVariable
    """
    pass


@dataclass
class Identifier(Primary):
    """Represents an OpenSCAD identifier (variable or function name).
    
    Identifiers are names used to refer to variables, functions, modules, and
    parameters in OpenSCAD code.
    
    Examples:
        x = 10;           // 'x' is an Identifier
        function foo() {} // 'foo' is an Identifier
        module bar() {}   // 'bar' is an Identifier
    
    Attributes:
        name: The identifier name as a string.
    """
    name: str

    def __str__(self):
        return self.name


@dataclass
class StringLiteral(Primary):
    """Represents an OpenSCAD string literal.
    
    String literals in OpenSCAD can be enclosed in either double quotes (")
    or single quotes (').
    
    Examples:
        "Hello, World!"
        'Single quoted string'
        "String with \"escaped\" quotes"
    
    Attributes:
        val: The string value without the surrounding quotes.
    """
    val: str

    def __str__(self):
        return f'"{self.val}"'


@dataclass
class NumberLiteral(Primary):
    """Represents an OpenSCAD numeric literal.
    
    OpenSCAD supports integers and floating-point numbers, including scientific
    notation.
    
    Examples:
        42              // Integer
        3.14            // Floating point
        1e10            // Scientific notation
        1.5e-3          // Scientific notation with negative exponent
        -10             // Negative number (handled by UnaryMinusOp)
    
    Attributes:
        val: The numeric value as a float.
    """
    val: float

    def __str__(self):
        return str(self.val)


@dataclass
class BooleanLiteral(Primary):
    """Represents an OpenSCAD boolean literal.
    
    OpenSCAD has two boolean values: true and false.
    
    Examples:
        x = true;
        y = false;
        if (condition) { ... }
    
    Attributes:
        val: The boolean value (True or False).
    """
    val: bool

    def __str__(self):
        return str(self.val)


@dataclass
class UndefinedLiteral(Primary):
    """Represents an OpenSCAD undefined literal.
    
    The 'undef' value in OpenSCAD represents an undefined or uninitialized value.
    It can be used in function parameters to indicate optional parameters.
    
    Examples:
        x = undef;
        function foo(x=undef) = x == undef ? 0 : x;
    
    Note:
        This class has no attributes as 'undef' is a keyword with no associated value.
    """

    def __str__(self):
        return "undef"


@dataclass 
class ParameterDeclaration(ASTNode):
    """Represents a parameter declaration in a function or module definition.
    
    Parameters can be declared with or without default values. Parameters without
    defaults are required when calling the function/module.
    
    Examples:
        function foo(x) = x;              // Required parameter
        function bar(x=10) = x;          // Optional parameter with default
        module test(a, b=2, c) { ... }  // Mixed required and optional
    
    Attributes:
        name: The parameter name as an Identifier.
        default: The default value expression, or None if no default is provided.
    """
    name: Identifier
    default: Expression|None

    def __str__(self):
        return f"{self.name}{f' = {self.default}' if self.default else '' }"
        

@dataclass
class Argument(ASTNode):
    """Base class for function and module call arguments.
    
    Arguments can be either positional (passed by position) or named
    (passed by name with the 'name=value' syntax).
    
    Examples:
        foo(1, 2)           // Positional arguments
        foo(a=1, b=2)       // Named arguments
        foo(1, b=2)         // Mixed arguments
    """
    pass


@dataclass
class PositionalArgument(Argument):
    """Represents a positional argument in a function or module call.
    
    Positional arguments are passed by their position in the argument list,
    without an explicit parameter name.
    
    Examples:
        foo(1, 2, 3)        // Three positional arguments
        cube(10)             // One positional argument
    
    Attributes:
        expr: The expression value of the argument.
    """
    expr: Expression

    def __str__(self):
        return f"{self.expr}"


@dataclass
class NamedArgument(Argument):
    """Represents a named argument in a function or module call.
    
    Named arguments use the 'name=value' syntax, allowing arguments to be
    passed in any order and making code more readable.
    
    Examples:
        cube(size=10)                    // Named argument
        translate(x=1, y=2, z=3)        // Multiple named arguments
        foo(1, b=2)                      // Mixed positional and named
    
    Attributes:
        name: The parameter name as an Identifier.
        expr: The expression value of the argument.
    """
    name: Identifier
    expr: Expression

    def __str__(self):
        return f"{self.name}={self.expr}"


@dataclass
class RangeLiteral(Primary):
    """Represents an OpenSCAD range literal.
    
    Ranges define sequences of numbers and are used in for loops and list
    comprehensions. The step value is optional in OpenSCAD syntax but required
    in the AST.
    
    Examples:
        [0:10]      // Range from 0 to 10 with step 1
        [0:10:2]    // Range from 0 to 10 with step 2
        [10:0:-1]   // Range from 10 to 0 with step -1
    
    Attributes:
        start: The starting value of the range.
        end: The ending value of the range.
        step: The step size between values.
    """
    start: Expression
    end: Expression
    step: Expression

    def __str__(self):
        return f"{self.start}:{self.end}:{self.step}"


@dataclass
class Assignment(ASTNode):
    """Represents a variable assignment in OpenSCAD.
    
    Assignments create or update variables. They can appear at the top level,
    within modules, or in let expressions and for loops.
    
    Examples:
        x = 10;                    // Simple assignment
        y = x + 5;                 // Assignment with expression
        let(a=1, b=2) a + b;       // Assignment in let expression
        for (i = [0:10]) { ... }   // Assignment in for loop
    
    Attributes:
        name: The variable name as an Identifier.
        expr: The expression value being assigned.
    """
    name: Identifier
    expr: Expression

    def __str__(self):
        return f"{self.name} = {self.expr}"


@dataclass
class LetOp(Expression):
    """Represents an OpenSCAD let expression.
    
    Let expressions allow local variable assignments within an expression scope.
    Variables defined in the let expression are only available in the body expression.
    
    Examples:
        let(a=1, b=2) a + b;           // Multiple assignments
        let(x=10) x * 2;               // Single assignment
        let(a=1) let(b=2) a + b;       // Nested let expressions
    
    Attributes:
        assignments: List of variable assignments local to this expression.
        body: The expression that uses the assigned variables.
    """
    assignments: list[Assignment]
    body: Expression

    def __str__(self):
        return f"let({', '.join(str(assignment) for assignment in self.assignments)}) {self.body}"


@dataclass
class EchoOp(Expression):
    """Represents an OpenSCAD echo expression.
    
    Echo expressions print values to the console during evaluation and return
    the body expression. Useful for debugging.
    
    Examples:
        echo("Value:", x) 5;           // Print and return 5
        echo(x, y, z) x + y + z;       // Print multiple values
    
    Attributes:
        arguments: List of arguments to print (can be positional or named).
        body: The expression to evaluate and return.
    """
    arguments: list[Argument]
    body: Expression

    def __str__(self):
        return f"echo({', '.join(str(arg) for arg in self.arguments)}) {self.body}"


@dataclass
class AssertOp(Expression):
    """Represents an OpenSCAD assert expression.
    
    Assert expressions check conditions and halt execution with an error message
    if the condition is false. If the condition is true, they return the body expression.
    
    Examples:
        assert(x > 0) x;               // Assert x is positive
        assert(condition=true, "Error") value;  // Assert with message
    
    Attributes:
        arguments: List of arguments (typically condition and optional message).
        body: The expression to return if assertion passes.
    """
    arguments: list[Argument]
    body: Expression

    def __str__(self):
        return f"assert({', '.join(str(arg) for arg in self.arguments)}) {self.body}"


@dataclass
class UnaryMinusOp(Expression):
    """Represents an OpenSCAD unary minus (negation) operation.
    
    Negates a numeric expression, making positive values negative and vice versa.
    
    Examples:
        -5                             // Result: -5
        -x                             // Negate variable
        -(x + y)                       // Negate expression
    
    Attributes:
        expr: The expression to negate.
    """
    expr: Expression

    def __str__(self):
        return f"-{self.expr}"


@dataclass
class AdditionOp(Expression):
    """Represents an OpenSCAD addition operation.
    
    Performs arithmetic addition of two expressions. Can be used with numbers
    or vectors (element-wise addition for vectors).
    
    Examples:
        1 + 2                          // Result: 3
        [1, 2, 3] + [4, 5, 6]         // Result: [5, 7, 9]
        x + y                          // Variable addition
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} + {self.right}"


@dataclass
class SubtractionOp(Expression):
    """Represents an OpenSCAD subtraction operation.
    
    Performs arithmetic subtraction of two expressions. Can be used with numbers
    or vectors (element-wise subtraction for vectors).
    
    Examples:
        5 - 2                          // Result: 3
        [5, 7, 9] - [1, 2, 3]          // Result: [4, 5, 6]
        x - y                          // Variable subtraction
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} - {self.right}"


@dataclass
class MultiplicationOp(Expression):
    """Represents an OpenSCAD multiplication operation.
    
    Performs arithmetic multiplication. Can multiply numbers, or a number by
    a vector (scalar multiplication).
    
    Examples:
        3 * 4                          // Result: 12
        2 * [1, 2, 3]                  // Result: [2, 4, 6]
        x * y                          // Variable multiplication
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} * {self.right}"


@dataclass
class DivisionOp(Expression):
    """Represents an OpenSCAD division operation.
    
    Performs arithmetic division. Can divide numbers, or divide a vector by
    a scalar (element-wise division).
    
    Examples:
        10 / 2                         // Result: 5
        [4, 6, 8] / 2                  // Result: [2, 3, 4]
        x / y                          // Variable division
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} / {self.right}"


@dataclass
class ModuloOp(Expression):
    """Represents an OpenSCAD modulo (remainder) operation.
    
    Returns the remainder after division. Works with integer and floating-point numbers.
    
    Examples:
        10 % 3                         // Result: 1
        15 % 4                         // Result: 3
        x % y                          // Variable modulo
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} % {self.right}"


@dataclass
class ExponentOp(Expression):
    """Represents an OpenSCAD exponentiation operation.
    
    Raises the left operand to the power of the right operand.
    
    Examples:
        2 ^ 3                          // Result: 8
        10 ^ 2                         // Result: 100
        x ^ y                          // Variable exponentiation
    
    Attributes:
        left: The base expression.
        right: The exponent expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} ^ {self.right}"


@dataclass
class BitwiseAndOp(Expression):
    """Represents an OpenSCAD bitwise AND operation.
    
    Performs bitwise AND on integer operands. Each bit of the result is 1
    only if both corresponding bits in the operands are 1.
    
    Examples:
        5 & 3                          // Result: 1 (binary: 101 & 011 = 001)
        12 & 7                         // Result: 4
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} & {self.right}"


@dataclass
class BitwiseOrOp(Expression):
    """Represents an OpenSCAD bitwise OR operation.
    
    Performs bitwise OR on integer operands. Each bit of the result is 1
    if either corresponding bit in the operands is 1.
    
    Examples:
        5 | 3                          // Result: 7 (binary: 101 | 011 = 111)
        12 | 7                         // Result: 15
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} | {self.right}"


@dataclass
class BitwiseNotOp(Expression):
    """Represents an OpenSCAD bitwise NOT (complement) operation.
    
    Performs bitwise NOT on an integer operand, inverting all bits.
    
    Examples:
        ~5                             // Inverts all bits of 5
        ~x                             // Bitwise NOT of variable
    
    Attributes:
        expr: The expression to complement.
    """
    expr: Expression

    def __str__(self):
        return f"~{self.expr}"


@dataclass
class BitwiseShiftLeftOp(Expression):
    """Represents an OpenSCAD bitwise left shift operation.
    
    Shifts the bits of the left operand to the left by the number of positions
    specified by the right operand. Equivalent to multiplying by 2^right.
    
    Examples:
        5 << 2                         // Result: 20 (5 * 2^2)
        1 << 3                         // Result: 8 (1 * 2^3)
    
    Attributes:
        left: The value to shift.
        right: The number of bits to shift left.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} << {self.right}"


@dataclass
class BitwiseShiftRightOp(Expression):
    """Represents an OpenSCAD bitwise right shift operation.
    
    Shifts the bits of the left operand to the right by the number of positions
    specified by the right operand. Equivalent to integer division by 2^right.
    
    Examples:
        20 >> 2                        // Result: 5 (20 / 2^2)
        8 >> 3                         // Result: 1 (8 / 2^3)
    
    Attributes:
        left: The value to shift.
        right: The number of bits to shift right.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} >> {self.right}"


@dataclass
class LogicalAndOp(Expression):
    """Represents an OpenSCAD logical AND operation.
    
    Returns true if both operands evaluate to true, false otherwise.
    Uses short-circuit evaluation (right operand not evaluated if left is false).
    
    Examples:
        true && false                  // Result: false
        x > 0 && y > 0                 // Both conditions must be true
        condition && action()          // action() only called if condition is true
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} && {self.right}"


@dataclass
class LogicalOrOp(Expression):
    """Represents an OpenSCAD logical OR operation.
    
    Returns true if either operand evaluates to true, false only if both are false.
    Uses short-circuit evaluation (right operand not evaluated if left is true).
    
    Examples:
        true || false                  // Result: true
        x < 0 || y < 0                 // At least one condition must be true
        condition || default()         // default() only called if condition is false
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} || {self.right}"


@dataclass
class LogicalNotOp(Expression):
    """Represents an OpenSCAD logical NOT operation.
    
    Inverts the boolean value of an expression. Returns true if the operand
    is false, and false if the operand is true.
    
    Examples:
        !true                          // Result: false
        !(x > 0)                       // Negate condition
        !condition                     // Logical NOT of variable
    
    Attributes:
        expr: The expression to negate.
    """
    expr: Expression

    def __str__(self):
        return f"!{self.expr}"


@dataclass
class TernaryOp(Expression):
    """Represents an OpenSCAD ternary (conditional) expression.
    
    Evaluates the condition and returns true_expr if condition is true,
    otherwise returns false_expr. Similar to if-else but as an expression.
    
    Examples:
        x > 0 ? x : -x                 // Absolute value
        condition ? 1 : 0              // Convert boolean to number
        x == 0 ? "zero" : "nonzero"    // Conditional string
    
    Attributes:
        condition: The boolean condition to evaluate.
        true_expr: Expression to return if condition is true.
        false_expr: Expression to return if condition is false.
    """
    condition: Expression
    true_expr: Expression
    false_expr: Expression

    def __str__(self):
        return f"{self.condition} ? {self.true_expr} : {self.false_expr}"


@dataclass
class EqualityOp(Expression):
    """Represents an OpenSCAD equality comparison operation.
    
    Returns true if both operands are equal, false otherwise.
    
    Examples:
        5 == 5                         // Result: true
        x == y                         // Compare variables
        [1, 2] == [1, 2]              // Compare vectors
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} == {self.right}"


@dataclass
class InequalityOp(Expression):
    """Represents an OpenSCAD inequality comparison operation.
    
    Returns true if operands are not equal, false if they are equal.
    
    Examples:
        5 != 3                         // Result: true
        x != y                         // Compare variables
        [1, 2] != [1, 3]              // Compare vectors
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} != {self.right}"


@dataclass
class GreaterThanOp(Expression):
    """Represents an OpenSCAD greater-than comparison operation.
    
    Returns true if the left operand is greater than the right operand.
    
    Examples:
        5 > 3                          // Result: true
        x > y                          // Compare variables
        10 > 10                        // Result: false
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} > {self.right}"


@dataclass
class GreaterThanOrEqualOp(Expression):
    """Represents an OpenSCAD greater-than-or-equal comparison operation.
    
    Returns true if the left operand is greater than or equal to the right operand.
    
    Examples:
        5 >= 3                         // Result: true
        5 >= 5                         // Result: true
        x >= y                         // Compare variables
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} >= {self.right}"


@dataclass
class LessThanOp(Expression):
    """Represents an OpenSCAD less-than comparison operation.
    
    Returns true if the left operand is less than the right operand.
    
    Examples:
        3 < 5                          // Result: true
        x < y                          // Compare variables
        10 < 10                        // Result: false
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} < {self.right}"


@dataclass
class LessThanOrEqualOp(Expression):
    """Represents an OpenSCAD less-than-or-equal comparison operation.
    
    Returns true if the left operand is less than or equal to the right operand.
    
    Examples:
        3 <= 5                         // Result: true
        5 <= 5                         // Result: true
        x <= y                         // Compare variables
    
    Attributes:
        left: The left operand expression.
        right: The right operand expression.
    """
    left: Expression
    right: Expression

    def __str__(self):
        return f"{self.left} <= {self.right}"


@dataclass
class FunctionLiteral(Expression):
    """Represents an OpenSCAD function literal (anonymous function).
    
    Function literals are anonymous functions that can be assigned to variables
    or used directly in expressions. They are defined using the 'function' keyword.
    
    Examples:
        x = function(x) x * 2;          // Anonymous function assigned to x
        function(a, b) a + b            // Function literal in expression
    
    Attributes:
        arguments: List of parameter declarations (as Argument nodes).
        body: The expression body of the function.
    """
    arguments: list[Argument]
    body: Expression

    def __str__(self):
        return f"function({', '.join(str(arg) for arg in self.arguments)}) {self.body}"


@dataclass
class PrimaryCall(Expression):
    """Represents an OpenSCAD function call expression.
    
    Function calls invoke a function with a list of arguments. The function
    can be referenced by an identifier or be the result of another expression.
    
    Examples:
        foo(1, 2)                       // Simple function call
        bar(x=1, y=2)                   // Named arguments
        obj.method(10)                  // Method call (chained)
        (function(x) x*2)(5)            // Call to function literal
    
    Attributes:
        left: The function expression (typically an Identifier).
        arguments: List of arguments (PositionalArgument or NamedArgument).
    """
    left: Expression
    arguments: list[Argument]

    def __str__(self):
        return f"{self.left}({', '.join(str(arg) for arg in self.arguments)})"


@dataclass
class PrimaryIndex(Expression):
    """Represents an OpenSCAD array/vector index access expression.
    
    Accesses an element of a vector or array by its index. Indices are 0-based.
    
    Examples:
        arr[0]                         // First element
        vec[i]                         // Element at index i
        matrix[2][3]                   // Nested indexing (chained)
        "string"[0]                    // Character access
    
    Attributes:
        left: The expression being indexed (vector, array, or string).
        index: The index expression (typically a NumberLiteral).
    """
    left: Expression
    index: Expression

    def __str__(self):
        return f"{self.left}[{self.index}]"


@dataclass
class PrimaryMember(Expression):
    """Represents an OpenSCAD member access expression.
    
    Accesses a member (property or method) of an object using dot notation.
    
    Examples:
        obj.member                      // Access object member
        vec.x                          // Access vector component
        obj.method()                   // Method access (chained with PrimaryCall)
    
    Attributes:
        left: The object expression.
        member: The member name as an Identifier.
    """
    left: Expression
    member: Identifier

    def __str__(self):
        return f"{self.left}.{self.member}"
        

@dataclass
class VectorElement(ASTNode):
    """Base class for elements in OpenSCAD list comprehensions.
    
    List comprehensions can contain various types of elements including
    simple expressions, let expressions, for loops, and conditionals.
    All such elements inherit from this base class.
    """
    def __str__(self):
        raise NotImplementedError
        

@dataclass
class ListCompLet(VectorElement):
    """Represents a let expression within a list comprehension.
    
    Allows local variable assignments within a list comprehension element.
    
    Examples:
        [let(x=1, y=2) x + y]          // Let in list comprehension
        [let(a=i) a * 2 for i=[0:5]]   // Let with for loop
    
    Attributes:
        assignments: List of local variable assignments.
        body: The expression body that uses the assigned variables.
    """
    assignments: list[Assignment]
    body: Expression

    def __str__(self):
        return f"let ({self.assignments}) {self.body}"
        

@dataclass
class ListCompEach(VectorElement):
    """Represents an 'each' expression within a list comprehension.
    
    The 'each' keyword flattens nested lists in list comprehensions,
    inserting all elements of a list rather than the list itself.
    
    Examples:
        [each [1, 2, 3]]               // Flattens to [1, 2, 3]
        [each [i, i+1] for i=[0:2]]   // Flattens nested lists
    
    Attributes:
        body: The vector element to flatten.
    """
    body: VectorElement

    def __str__(self):
        return f"each {self.body}"
        

@dataclass
class ListCompFor(VectorElement):
    """Represents a for loop within a list comprehension.
    
    Iterates over a range or list, generating elements for each iteration.
    This is the simple form of for loop (not C-style).
    
    Examples:
        [i for i=[0:5]]                // Generate list [0, 1, 2, 3, 4]
        [i*2 for i=[0:3]]              // Generate [0, 2, 4]
        [x, y for x=[0:2], y=[0:2]]   // Nested loops
    
    Attributes:
        assignments: List of loop variable assignments.
        body: The expression to evaluate for each iteration.
    """
    assignments: list[Assignment]
    body: VectorElement

    def __str__(self):
        return f"for ({self.assignments}) {self.body}"
        

@dataclass
class ListCompCStyleFor(VectorElement):
    """Represents a C-style for loop within a list comprehension.
    
    C-style for loops have three parts: initialization, condition, and increment.
    Similar to C/Java for loops: for (init; condition; increment) body
    
    Examples:
        [i for (i=0; i<5; i=i+1)]      // C-style for loop
        [i*2 for (i=0; i<10; i=i+2)]   // With increment step
    
    Attributes:
        initial: List of initialization assignments.
        condition: The loop continuation condition.
        increment: List of increment assignments.
        body: The expression to evaluate for each iteration.
    """
    initial: list[Assignment]
    condition: Expression
    increment: list[Assignment]
    body: VectorElement

    def __str__(self):
        return f"for ({self.initial}; {self.condition}; {self.increment}) {self.body}"
        

@dataclass
class ListCompIf(VectorElement):
    """Represents an if condition within a list comprehension.
    
    Conditionally includes elements in a list comprehension based on a condition.
    If the condition is false, no element is added (not the same as adding undef).
    
    Examples:
        [i for i=[0:5] if i%2==0]      // Only even numbers
        [x if x>0 for x=[-2:3]]        // Only positive values
    
    Attributes:
        condition: The boolean condition to evaluate.
        true_expr: The expression to include if condition is true.
    """
    condition: Expression
    true_expr: VectorElement

    def __str__(self):
        return f"if {self.condition} {self.true_expr}"


@dataclass
class ListCompIfElse(VectorElement):
    """Represents an if-else condition within a list comprehension.
    
    Conditionally includes one of two expressions in a list comprehension
    based on a condition.
    
    Examples:
        [i>0 ? i : -i for i=[-2:3]]    // Absolute value
        [x%2==0 ? x : x+1 for x=[0:5]] // Make all even
    
    Attributes:
        condition: The boolean condition to evaluate.
        true_expr: The expression to include if condition is true.
        false_expr: The expression to include if condition is false.
    """
    condition: Expression
    true_expr: VectorElement
    false_expr: VectorElement

    def __str__(self):
        return f"if {self.condition} {self.true_expr} else {self.false_expr}"


@dataclass
class ListComprehension(Expression):
    """Represents an OpenSCAD list comprehension (vector literal).
    
    List comprehensions generate lists dynamically using loops, conditions,
    and expressions. They are enclosed in square brackets.
    
    Examples:
        [1, 2, 3]                      // Simple list
        [i for i=[0:5]]                // Generated list
        [i*2 for i=[0:5] if i>0]      // With condition
        [let(x=i) x+1 for i=[0:3]]    // With let expression
    
    Attributes:
        elements: List of vector elements (expressions, for loops, conditions, etc.).
    """
    elements: list[VectorElement]
    
    def __str__(self):
        return f"[{', '.join(str(element) for element in self.elements)}]"
        

@dataclass
class ModuleInstantiation(ASTNode):
    """Base class for all OpenSCAD module instantiations.
    
    Module instantiations are statements that create 3D objects or perform
    transformations. This includes module calls, for loops, conditionals,
    and modifiers. All module-related statements inherit from this class.
    """
    pass


@dataclass
class ModularCall(ModuleInstantiation):
    """Represents a module call (module instantiation).
    
    Module calls invoke a module with arguments. Modules can have child
    module instantiations (transformations applied to children).
    
    Examples:
        cube(10);                      // Simple module call
        translate([1, 2, 3]) cube(10); // Module with child
        cube(size=10, center=true);    // Named arguments
    
    Attributes:
        name: The module name as an Identifier.
        arguments: List of arguments (PositionalArgument or NamedArgument).
        children: List of child module instantiations (for transformations).
    """
    name: Identifier
    arguments: list[Argument]
    children: list[ModuleInstantiation]

    def __str__(self):
        return f"{self.name}({', '.join(str(arg) for arg in self.arguments)})"
        

@dataclass
class ModularFor(ModuleInstantiation):
    """Represents a for loop module instantiation.
    
    Iterates over a range or list, instantiating the body module for each iteration.
    This is the simple form of for loop (not C-style).
    
    Examples:
        for (i=[0:5]) translate([i, 0, 0]) cube(1);
        for (x=[0:2], y=[0:2]) translate([x, y, 0]) sphere(1);
    
    Attributes:
        assignments: List of loop variable assignments.
        body: The module instantiation to execute for each iteration.
    """
    assignments: list[Assignment]
    body: ModuleInstantiation

    def __str__(self):
        return f"for ({', '.join(str(assignment) for assignment in self.assignments)}) {self.body}"
        

@dataclass
class ModularCLikeFor(ModuleInstantiation):
    """Represents a C-style for loop module instantiation.
    
    C-style for loops have three parts: initialization, condition, and increment.
    Similar to C/Java for loops: for (init; condition; increment) body
    
    Examples:
        for (i=0; i<5; i=i+1) translate([i, 0, 0]) cube(1);
        for (i=0; i<10; i=i+2) rotate([0, 0, i]) cube(1);
    
    Attributes:
        initial: List of initialization assignments.
        condition: The loop continuation condition.
        increment: List of increment assignments.
        body: The module instantiation to execute for each iteration.
    """
    initial: list[Assignment]
    condition: Expression
    increment: list[Assignment]
    body: ModuleInstantiation

    def __str__(self):
        return f"for ({'; '.join(str(a) for a in self.initial)}; {self.condition}; {', '.join(str(a) for a in self.increment)}) {self.body}"
    

@dataclass
class ModularIntersectionFor(ModuleInstantiation):
    """Represents an intersection_for loop module instantiation.
    
    Similar to a regular for loop, but computes the intersection of all
    iterations rather than the union. Used for creating complex intersections.
    
    Examples:
        intersection_for (i=[0:3]) rotate([0, 0, i*90]) cube(10);
    
    Attributes:
        assignments: List of loop variable assignments.
        body: The module instantiation to execute for each iteration.
    """
    assignments: list[Assignment]
    body: ModuleInstantiation

    def __str__(self):
        return f"intersection_for ({', '.join(str(assignment) for assignment in self.assignments)}) {self.body}"
        

@dataclass
class ModularLet(ModuleInstantiation):
    """Represents a let statement for module instantiations.
    
    Allows local variable assignments within a module scope. Variables are
    available to all child module instantiations.
    
    Examples:
        let (x=10, y=20) {
            translate([x, y, 0]) cube(1);
            sphere(5);
        }
    
    Attributes:
        assignments: List of local variable assignments.
        children: List of child module instantiations that can use the variables.
    """
    assignments: list[Assignment]
    children: list[ModuleInstantiation]

    def __str__(self):
        return f"let ({', '.join(str(assignment) for assignment in self.assignments)}) {', '.join(str(child) for child in self.children)}"
        

@dataclass
class ModularEcho(ModuleInstantiation):
    """Represents an echo statement for module instantiations.
    
    Prints values to the console during rendering and then renders the children.
    Useful for debugging module execution.
    
    Examples:
        echo("Rendering cube") cube(10);
        echo(x, y, z) translate([x, y, z]) sphere(5);
    
    Attributes:
        arguments: List of arguments to print (can be positional or named).
        children: List of child module instantiations to render.
    """
    arguments: list[Argument]
    children: list[ModuleInstantiation]

    def __str__(self):
        return f"echo({', '.join(str(arg) for arg in self.arguments)}) {', '.join(str(child) for child in self.children)}"
    

@dataclass
class ModularAssert(ModuleInstantiation):
    """Represents an assert statement for module instantiations.
    
    Checks conditions and halts rendering with an error message if the condition
    is false. If true, renders the children.
    
    Examples:
        assert(x > 0, "x must be positive") cube(x);
        assert(condition=true, "Error message") sphere(5);
    
    Attributes:
        arguments: List of arguments (typically condition and optional message).
        children: List of child module instantiations to render if assertion passes.
    """
    arguments: list[Argument]
    children: list[ModuleInstantiation]

    def __str__(self):
        return f"assert({', '.join(str(arg) for arg in self.arguments)}) {', '.join(str(child) for child in self.children)}"
    

@dataclass
class ModularIf(ModuleInstantiation):
    """Represents an if statement for module instantiations (without else).
    
    Conditionally renders a module instantiation based on a condition.
    If the condition is false, nothing is rendered.
    
    Examples:
        if (x > 0) cube(x);
        if (condition) translate([1, 2, 3]) sphere(5);
    
    Attributes:
        condition: The boolean condition to evaluate.
        true_branch: The module instantiation to render if condition is true.
    """
    condition: Expression
    true_branch: ModuleInstantiation

    def __str__(self):
        return f"if ({self.condition}) {self.true_branch}"


@dataclass
class ModularIfElse(ModuleInstantiation):
    """Represents an if-else statement for module instantiations.
    
    Conditionally renders one of two module instantiations based on a condition.
    
    Examples:
        if (x > 0) cube(x) else sphere(5);
        if (condition) translate([1, 0, 0]) cube(1) else translate([0, 1, 0]) sphere(1);
    
    Attributes:
        condition: The boolean condition to evaluate.
        true_branch: The module instantiation to render if condition is true.
        false_branch: The module instantiation to render if condition is false.
    """
    condition: Expression
    true_branch: ModuleInstantiation
    false_branch: ModuleInstantiation

    def __str__(self):
        return f"if ({self.condition}) {self.true_branch} else {self.false_branch}"


@dataclass
class ModularModifierShowOnly(ModuleInstantiation):
    """Represents the '!' (show only) module modifier.
    
    The '!' modifier shows only this module instantiation, hiding all others
    at the same level. Useful for debugging specific parts of a model.
    
    Examples:
        !cube(10);                     // Show only this cube
        !translate([1, 2, 3]) sphere(5);
    
    Attributes:
        child: The module instantiation to show exclusively.
    """
    child: ModuleInstantiation

    def __str__(self):
        return f"!{self.child}"

@dataclass
class ModularModifierHighlight(ModuleInstantiation):
    """Represents the '#' (highlight) module modifier.
    
    The '#' modifier highlights this module instantiation in a different color,
    making it stand out from other geometry. Useful for debugging.
    
    Examples:
        #cube(10);                     // Highlight this cube
        #translate([1, 2, 3]) sphere(5);
    
    Attributes:
        child: The module instantiation to highlight.
    """
    child: ModuleInstantiation

    def __str__(self):
        return f"#{self.child}"


@dataclass
class ModularModifierBackground(ModuleInstantiation):
    """Represents the '%' (background) module modifier.
    
    The '%' modifier renders this module instantiation as a semi-transparent
    background, allowing other geometry to show through. Useful for visualizing
    hidden or internal geometry.
    
    Examples:
        %cube(10);                     // Render as background
        %translate([1, 2, 3]) sphere(5);
    
    Attributes:
        child: The module instantiation to render as background.
    """
    child: ModuleInstantiation

    def __str__(self):
        return f"%{self.child}"


@dataclass
class ModularModifierDisable(ModuleInstantiation):
    """Represents the '*' (disable) module modifier.
    
    The '*' modifier disables this module instantiation, preventing it from
    being rendered. Useful for temporarily removing parts of a model.
    
    Examples:
        *cube(10);                     // Disable this cube
        *translate([1, 2, 3]) sphere(5);
    
    Attributes:
        child: The module instantiation to disable.
    """
    child: ModuleInstantiation

    def __str__(self):
        return f"*{self.child}"


@dataclass
class ModuleDeclaration(ASTNode):
    """Represents an OpenSCAD module declaration (definition).
    
    Module declarations define reusable 3D objects or operations. Modules
    can have parameters and contain module instantiations in their body.
    
    Examples:
        module cube(size) { ... }
        module test(x, y=2) {
            translate([x, y, 0]) cube(1);
        }
    
    Attributes:
        name: The module name as an Identifier.
        parameters: List of parameter declarations.
        children: List of module instantiations in the module body.
    """
    name: Identifier
    parameters: list[ParameterDeclaration]
    children: list[ModuleInstantiation]

    def __str__(self):
        params = ', '.join(str(param) for param in self.parameters)
        children = ', '.join(str(child) for child in self.children)
        return f"module {self.name}({params}) {{ {children} }}"


@dataclass
class FunctionDeclaration(ASTNode):
    """Represents an OpenSCAD function declaration (definition).
    
    Function declarations define reusable expressions. Functions must return
    a single expression value and cannot have side effects.
    
    Examples:
        function add(x, y) = x + y;
        function square(x) = x * x;
        function test(x, y=2) = x + y;
    
    Attributes:
        name: The function name as an Identifier.
        parameters: List of parameter declarations.
        expr: The expression body that the function evaluates to.
    """
    name: Identifier
    parameters: list[ParameterDeclaration]
    expr: Expression

    def __str__(self):
        params = ', '.join(str(param) for param in self.parameters)
        return f"function {self.name}({params}) = {self.expr};"


@dataclass
class UseStatement(ASTNode):
    """Represents an OpenSCAD 'use' statement.
    
    The 'use' statement imports function and module definitions from another
    file. Functions and modules from the used file become available in the
    current file. Unlike 'include', 'use' does not execute top-level code.
    
    Examples:
        use <library.scad>
        use <utils/math.scad>
    
    Attributes:
        filepath: The file path as a StringLiteral (without angle brackets).
    """
    filepath: StringLiteral

    def __str__(self):
        return f"use <{self.filepath.val}>"


@dataclass
class IncludeStatement(ASTNode):
    """Represents an OpenSCAD 'include' statement.
    
    The 'include' statement includes and executes all code from another file
    at the point where it appears. This includes function/module definitions
    and any top-level statements.
    
    Examples:
        include <library.scad>
        include <utils/math.scad>
    
    Attributes:
        filepath: The file path as a StringLiteral (without angle brackets).
    """
    filepath: StringLiteral

    def __str__(self):
        return f"include <{self.filepath.val}>"



class ASTBuilderVisitor(PTNodeVisitor):
    """
    Visits the parse tree generated by the PEG grammar in __init__.py and builds the AST defined in ast.py.
    """
    
    def __init__(self, parser, file=""):
        """Initialize the visitor with the parser and optional file path.
        
        Args:
            parser: The Arpeggio parser instance (needed to access input for position conversion)
            file: Optional file path for source location tracking
        """
        super().__init__()
        self.parser = parser
        self.file = file
    
    def visit_parse_tree(self, parse_tree):
        """Visit a parse tree and return the AST.
        
        This is the main entry point for converting a parse tree to an AST.
        
        Args:
            parse_tree: The root node of an Arpeggio parse tree
            
        Returns:
            The root AST node (or list of AST nodes for the root level)
        """
        return self._visit_node(parse_tree)
    
    def _visit_node(self, node):
        """Recursively visit a parse tree node and return AST.
        
        This method handles the visitor pattern for Arpeggio parse trees.
        Terminal nodes are passed through as their values, and NonTerminal nodes
        are visited using their rule_name to find the appropriate visit method.
        NonTerminal nodes without visit methods are passed through as the node itself.
        
        Args:
            node: An Arpeggio parse tree node
            
        Returns:
            The AST node (or list of AST nodes) for this parse tree node,
            or the node/value itself if it should be passed through
        """
        if node is None:
            return None
        
        # Get the rule name for this node
        if not hasattr(node, 'rule_name'):
            # Terminal node - return its value so parent can use it directly
            return getattr(node, 'value', node)
        
        rule_name = node.rule_name
        
        # Visit children first
        # Arpeggio's NonTerminal objects are iterable, so iterate directly
        children = []
        try:
            # Try to iterate over the node (Arpeggio NonTerminal objects are iterable)
            for child in node:
                child_ast = self._visit_node(child)
                if child_ast is not None:
                    # If child_ast is a list, extend; otherwise append
                    if isinstance(child_ast, list):
                        children.extend(child_ast)
                    else:
                        children.append(child_ast)
        except (TypeError, AttributeError):
            # Node is not iterable, skip children
            pass
        
        # Call the appropriate visit method
        visit_method_name = f"visit_{rule_name}"
        visit_method = getattr(self, visit_method_name, None)
        if visit_method:
            try:
                return visit_method(node, children)
            except Exception as e:
                # If visit method fails, return children or None
                return children if children else None
        else:
            # No visit method - pass through the node itself so parent can access rule_name/value
            # This is useful for operator nodes like TOK_BINARY_OR, TOK_EQUAL, etc.
            return node
    
    def _get_node_position(self, node):
        """Extract position information from an Arpeggio parse tree node.
        
        Stores only the character position. Line and column are calculated
        lazily when accessed.
        
        Args:
            node: Arpeggio parse tree node
            
        Returns:
            Position object for the node (with character position only)
        """
        input_str = self.parser.input if hasattr(self.parser, 'input') else ""
        if hasattr(node, 'position'):
            return Position(file=self.file, position=node.position, input_str=input_str)
        return Position(file=self.file, position=0, input_str=input_str)

    def visit_TOK_ID(self, node, children):
        # Prefer the last child for value (to avoid list-wrapping problems)
        value = children[-1] if children else node.value
        return Identifier(
            name=value,
            position=self._get_node_position(node)
        )

    def visit_TOK_STRING(self, node, children):
        # TOK_STRING has 3 children: opening quote, string content, closing quote
        # We want the middle child (index 1) which is the actual string content
        # Terminal nodes return None from _visit_node, so we need to access raw children
        try:
            node_children = list(node)
            if len(node_children) >= 2:
                # node_children[1] is the Terminal node with the string content
                value = node_children[1].value if hasattr(node_children[1], 'value') else str(node_children[1])
            else:
                # Fallback: use node.value and extract string content
                value = node.value
                if isinstance(value, str):
                    # Extract the middle part if node.value is like '" | hello | "'
                    parts = value.split(' | ')
                    if len(parts) == 3:
                        value = parts[1]
                    elif value.startswith('"') and value.endswith('"'):
                        value = value.strip('"')
        except (TypeError, AttributeError, IndexError):
            # Fallback: use node.value
            value = node.value
            if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                # Extract the middle part if node.value is like '" | hello | "'
                parts = value.split(' | ')
                if len(parts) == 3:
                    value = parts[1]
                else:
                    value = value.strip('"')
        return StringLiteral(
            val=value,
            position=self._get_node_position(node)
        )

    def visit_TOK_NUMBER(self, node, children):
        value = children[-1] if children else node.value
        return NumberLiteral(
            val=float(value),
            position=self._get_node_position(node)
        )
    
    def visit_TOK_TRUE(self, node, children):
        return BooleanLiteral(
            val=True,
            position=self._get_node_position(node)
        )

    def visit_TOK_FALSE(self, node, children):
        return BooleanLiteral(
            val=False,
            position=self._get_node_position(node)
        )

    def visit_TOK_UNDEF(self, node, children):
        return UndefinedLiteral(position=self._get_node_position(node))
    
    def visit_module_definition(self, node, children):
        # module_definition rule: (TOK_MODULE, TOK_ID, '(', parameters, ')', statement)
        # After visiting, children structure: [name (Identifier), parameters (list or None), statement (body)]
        # Terminal nodes (TOK_MODULE, '(', ')') return None, so they're filtered out
        
        # Find name (Identifier)
        name = None
        for child in children:
            if isinstance(child, Identifier):
                name = child
                break
        
        if name is None:
            raise ValueError("module_definition should have a name (Identifier)")
        
        # Find parameters (list of ParameterDeclaration)
        # Parameters could be:
        # 1. A list of ParameterDeclaration nodes (from visit_parameters)
        # 2. Individual ParameterDeclaration nodes
        params = []
        for child in children:
            if isinstance(child, list):
                # List of parameters
                params.extend([item for item in child if isinstance(item, ParameterDeclaration)])
            elif isinstance(child, ParameterDeclaration):
                # Single parameter
                params.append(child)
        
        # Find statement body and extract module instantiations
        # The statement body could be:
        # 1. A single statement (ModuleInstantiation, Assignment, etc.)
        # 2. A list of statements (from a block '{ ... }')
        mods = []
        for child in children:
            if isinstance(child, ModuleInstantiation):
                # Direct module instantiation
                mods.append(child)
            elif isinstance(child, list):
                # Block of statements
                for item in child:
                    if isinstance(item, ModuleInstantiation):
                        mods.append(item)
                    elif isinstance(item, list):
                        # Nested lists (from nested blocks)
                        for nested_item in item:
                            if isinstance(nested_item, ModuleInstantiation):
                                mods.append(nested_item)
            # Note: Assignment nodes are not included in children, only ModuleInstantiation nodes
        
        return ModuleDeclaration(
            name=name,
            parameters=params,
            children=mods,
            position=self._get_node_position(node)
        )

    def visit_function_definition(self, node, children):
        # function_definition rule: (TOK_FUNCTION, TOK_ID, '(', parameters, ')', TOK_ASSIGN, expr, ';')
        # After visiting, children are: [Terminal (TOK_FUNCTION), Identifier (name), Terminal ('('), 
        #   ParameterDeclaration, ..., ParameterDeclaration, Terminal (')'), Terminal (TOK_ASSIGN), 
        #   Expression (expr), Terminal (';')]
        # Terminal nodes are now passed through from _visit_node, so we need to filter them out
        
        # Get the name (should be an Identifier)
        name = None
        for child in children:
            if isinstance(child, Identifier):
                name = child
                break
        
        if name is None:
            raise ValueError("FunctionDeclarationNode should have an Identifier child for the name")
        
        # Collect all ParameterDeclaration nodes (they come after the name)
        params = [item for item in children if isinstance(item, ParameterDeclaration)]
        
        # Get the expression (should be an Expression that's not the Identifier name)
        # Filter for Expression instances, excluding the Identifier name
        expr_candidates = [item for item in children if isinstance(item, Expression) and item is not name]
        expr = expr_candidates[-1] if expr_candidates else None
        if expr is None:
            raise ValueError("FunctionDeclarationNode should have an Expression child")
        
        return FunctionDeclaration(
            name=name,
            parameters=params,
            expr=expr,
            position=self._get_node_position(node)
        )
    
    def visit_use_statement(self, node, children):
        # use_statement rule: (TOK_USE, '<', _(r'[^>]+'), '>')
        # The filepath is at index 2 in the raw node children (the regex match)
        # Terminal nodes return None from _visit_node, so we need to access raw children
        try:
            node_children = list(node)
            if len(node_children) >= 3:
                # node_children[2] is the Terminal node with the filepath
                filepath_value = node_children[2].value if hasattr(node_children[2], 'value') else str(node_children[2])
                filepath = StringLiteral(val=filepath_value, position=self._get_node_position(node_children[2]))
            else:
                raise ValueError("UseStatementNode should have a filepath at index 2")
        except (TypeError, AttributeError, IndexError):
            # Fallback: try to find StringLiteral in children
            strlits = [child for child in children if isinstance(child, StringLiteral)]
            if strlits:
                filepath = strlits[0]
            else:
                raise ValueError("UseStatementNode should have a filepath")
        
        return UseStatement(
            filepath=filepath,
            position=self._get_node_position(node)
        )
    
    def visit_include_statement(self, node, children):
        # include_statement rule: (TOK_INCLUDE, '<', _(r'[^>]+'), '>')
        # The filepath is at index 2 in the raw node children (the regex match)
        # Terminal nodes return None from _visit_node, so we need to access raw children
        try:
            node_children = list(node)
            if len(node_children) >= 3:
                # node_children[2] is the Terminal node with the filepath
                filepath_value = node_children[2].value if hasattr(node_children[2], 'value') else str(node_children[2])
                filepath = StringLiteral(val=filepath_value, position=self._get_node_position(node_children[2]))
            else:
                raise ValueError("IncludeStatementNode should have a filepath at index 2")
        except (TypeError, AttributeError, IndexError):
            # Fallback: try to find StringLiteral in children
            strlits = [child for child in children if isinstance(child, StringLiteral)]
            if strlits:
                filepath = strlits[0]
            else:
                raise ValueError("IncludeStatementNode should have a filepath")
        
        return IncludeStatement(
            filepath=filepath,
            position=self._get_node_position(node)
        )

    def visit_parameters(self, node, children):
        # parameters rule: (ZeroOrMore(parameter, sep=TOK_COMMA), ZeroOrMore(TOK_COMMA))
        # Collect all ParameterDeclaration nodes, filtering out commas and empty elements
        params = [child for child in children if isinstance(child, ParameterDeclaration)]
        return params
    
    def visit_parameter(self, node, children):
        # parameter rule: [(TOK_ID, TOK_ASSIGN, expr), TOK_ID]
        if len(children) == 1:
            # Just TOK_ID - no default value
            name = children[0] if isinstance(children[0], Identifier) else Identifier(name=children[0], position=self._get_node_position(node))
            return ParameterDeclaration(name=name, default=None, position=self._get_node_position(node))
        else:
            # TOK_ID, TOK_ASSIGN, expr
            name = children[0] if isinstance(children[0], Identifier) else Identifier(name=children[0], position=self._get_node_position(node))
            default_expr = [child for child in children[1:] if isinstance(child, Expression)]
            default = default_expr[0] if default_expr else None
            return ParameterDeclaration(name=name, default=default, position=self._get_node_position(node))
    
    def visit_arguments(self, node, children):
        # arguments rule: (ZeroOrMore(argument, sep=TOK_COMMA), Optional(TOK_COMMA))
        # Collect all Argument nodes (PositionalArgument or NamedArgument), filtering out commas
        args = [child for child in children if isinstance(child, Argument)]
        return args
    
    def visit_argument(self, node, children):
        # argument rule: [(TOK_ID, TOK_ASSIGN, expr), expr]
        if len(children) == 1:
            # Just expr - positional argument
            expr = children[0] if isinstance(children[0], Expression) else None
            if expr is None:
                raise ValueError("argument should have an Expression child")
            return PositionalArgument(expr=expr, position=self._get_node_position(node))
        else:
            # TOK_ID, TOK_ASSIGN, expr - named argument
            name = children[0] if isinstance(children[0], Identifier) else Identifier(name=children[0], position=self._get_node_position(node))
            expr = [child for child in children[1:] if isinstance(child, Expression)]
            if not expr:
                raise ValueError("named argument should have an Expression child")
            return NamedArgument(name=name, expr=expr[0], position=self._get_node_position(node))
    
    def visit_assignments_expr(self, node, children):
        # assignments_expr rule: (ZeroOrMore(assignment_expr, sep=TOK_COMMA), Optional(TOK_COMMA))
        # Collect all Assignment nodes, filtering out commas
        assignments = [child for child in children if isinstance(child, Assignment)]
        return assignments
    
    def visit_assignment_expr(self, node, children):
        # assignment_expr rule: (TOK_ID, TOK_ASSIGN, expr)
        name = children[0] if isinstance(children[0], Identifier) else Identifier(name=children[0], position=self._get_node_position(node))
        expr = [child for child in children[1:] if isinstance(child, Expression)]
        if not expr:
            raise ValueError("assignment_expr should have an Expression child")
        return Assignment(name=name, expr=expr[0], position=self._get_node_position(node))
    
    def visit_let_expr(self, node, children):
        # let_expr rule: (TOK_LET, '(', assignments_expr, ')', expr)
        # children: assignments list, expr
        assignments = [child for child in children if isinstance(child, Assignment)]
        expr = [child for child in children if isinstance(child, Expression) and not isinstance(child, Assignment)]
        if not expr:
            raise ValueError("let_expr should have an Expression body")
        return LetOp(assignments=assignments, body=expr[0], position=self._get_node_position(node))
    
    def visit_assert_expr(self, node, children):
        # assert_expr rule: (TOK_ASSERT, '(', arguments, ')', Optional(expr))
        arguments = [child for child in children if isinstance(child, Argument)]
        expr = [child for child in children if isinstance(child, Expression) and not isinstance(child, Argument)]
        body = expr[0] if expr else None
        if body is None:
            raise ValueError("assert_expr should have an Expression body")
        return AssertOp(arguments=arguments, body=body, position=self._get_node_position(node))
    
    def visit_echo_expr(self, node, children):
        # echo_expr rule: (TOK_ECHO, '(', arguments, ')', Optional(expr))
        arguments = [child for child in children if isinstance(child, Argument)]
        expr = [child for child in children if isinstance(child, Expression) and not isinstance(child, Argument)]
        body = expr[0] if expr else None
        if body is None:
            raise ValueError("echo_expr should have an Expression body")
        return EchoOp(arguments=arguments, body=body, position=self._get_node_position(node))
    
    def visit_ternary_expr(self, node, children):
        # ternary_expr rule: (prec_logical_or, '?', expr, ':', expr)
        # children: condition, true_expr, false_expr
        exprs = [child for child in children if isinstance(child, Expression)]
        if len(exprs) != 3:
            raise ValueError("ternary_expr should have 3 Expression children (condition, true, false)")
        return TernaryOp(condition=exprs[0], true_expr=exprs[1], false_expr=exprs[2], position=self._get_node_position(node))
    
    def visit_prec_logical_or(self, node, children):
        # prec_logical_or rule: OneOrMore(prec_logical_and, sep=TOK_LOGICAL_OR)
        # Build left-associative tree
        if len(children) == 1:
            return children[0]
        result = children[0]
        for i in range(1, len(children)):
            result = LogicalOrOp(left=result, right=children[i], position=self._get_node_position(node))
        return result
    
    def visit_prec_logical_and(self, node, children):
        # prec_logical_and rule: OneOrMore(prec_equality, sep=TOK_LOGICAL_AND)
        if len(children) == 1:
            return children[0]
        result = children[0]
        for i in range(1, len(children)):
            result = LogicalAndOp(left=result, right=children[i], position=self._get_node_position(node))
        return result
    
    def visit_prec_equality(self, node, children):
        # prec_equality rule: OneOrMore(prec_comparison, sep=[TOK_EQUAL, TOK_NOTEQUAL])
        # The node structure is: [prec_comparison, operator, prec_comparison, operator, ...]
        # But Terminal nodes (operators) return None from _visit_node, so we need to access raw children
        if len(children) == 1:
            return children[0]
        
        # Get raw node children to access operators
        try:
            node_children = list(node)
            # node_children alternates: operand, operator, operand, operator, ...
            # children list has only the operands (Terminal nodes filtered out)
            result = children[0]
            operand_idx = 1  # Index into children list (operands only)
            
            for i in range(1, len(node_children), 2):  # Skip every other (operators)
                if i < len(node_children):
                    operator_node = node_children[i]
                    # Check if it's TOK_EQUAL or TOK_NOTEQUAL
                    if hasattr(operator_node, 'rule_name'):
                        if operator_node.rule_name == 'TOK_EQUAL':
                            operator = '=='
                        elif operator_node.rule_name == 'TOK_NOTEQUAL':
                            operator = '!='
                        else:
                            operator = operator_node.value if hasattr(operator_node, 'value') else str(operator_node)
                    else:
                        operator = operator_node.value if hasattr(operator_node, 'value') else str(operator_node)
                    
                    if operand_idx < len(children):
                        right_operand = children[operand_idx]
                        if operator == '==' or operator == 'TOK_EQUAL':
                            result = EqualityOp(left=result, right=right_operand, position=self._get_node_position(node))
                        elif operator == '!=' or operator == 'TOK_NOTEQUAL':
                            result = InequalityOp(left=result, right=right_operand, position=self._get_node_position(node))
                        else:
                            # Default to equality if unknown operator
                            result = EqualityOp(left=result, right=right_operand, position=self._get_node_position(node))
                        operand_idx += 1
        except (TypeError, AttributeError, IndexError):
            # Fallback: if we can't access raw children, default to equality
            result = children[0]
            for i in range(1, len(children)):
                result = EqualityOp(left=result, right=children[i], position=self._get_node_position(node))
        
        return result
    
    def visit_prec_comparison(self, node, children):
        # prec_comparison rule: OneOrMore(prec_binary_or, sep=[TOK_LTE, TOK_GTE, TOK_LT, TOK_GT])
        # The node structure is: [prec_binary_or, operator, prec_binary_or, operator, ...]
        # Operators are NonTerminal nodes with rule_name TOK_LT, TOK_GT, TOK_LTE, or TOK_GTE
        if len(children) == 1:
            return children[0]
        
        # Get raw node children to access operators
        try:
            node_children = list(node)
            # node_children alternates: operand, operator, operand, operator, ...
            # children list has only the operands (operators might be filtered out or included)
            result = children[0]
            operand_idx = 1  # Index into children list (operands only)
            
            for i in range(1, len(node_children), 2):  # Skip every other (operators)
                if i < len(node_children):
                    operator_node = node_children[i]
                    # Check the rule_name to determine the operator
                    if hasattr(operator_node, 'rule_name'):
                        operator_rule = operator_node.rule_name
                    else:
                        operator_rule = None
                    
                    if operand_idx < len(children):
                        right_operand = children[operand_idx]
                        if operator_rule == 'TOK_LT':
                            result = LessThanOp(left=result, right=right_operand, position=self._get_node_position(node))
                        elif operator_rule == 'TOK_GT':
                            result = GreaterThanOp(left=result, right=right_operand, position=self._get_node_position(node))
                        elif operator_rule == 'TOK_LTE':
                            result = LessThanOrEqualOp(left=result, right=right_operand, position=self._get_node_position(node))
                        elif operator_rule == 'TOK_GTE':
                            result = GreaterThanOrEqualOp(left=result, right=right_operand, position=self._get_node_position(node))
                        else:
                            # Default to less than if unknown operator
                            result = LessThanOp(left=result, right=right_operand, position=self._get_node_position(node))
                        operand_idx += 1
        except (TypeError, AttributeError, IndexError):
            # Fallback: if we can't access raw children, default to less than
            result = children[0]
            for i in range(1, len(children)):
                result = LessThanOp(left=result, right=children[i], position=self._get_node_position(node))
        
        return result
    
    def visit_prec_binary_or(self, node, children):
        # prec_binary_or rule: OneOrMore(prec_binary_and, sep=TOK_BINARY_OR)
        # The children list contains: operands (AST nodes) and operators (NonTerminal nodes with rule_name TOK_BINARY_OR)
        # Operators are passed through from _visit_node since there's no visit_TOK_BINARY_OR method
        if len(children) == 1:
            return children[0]
        
        # Separate operands (Expression AST nodes) from operators (NonTerminal nodes with rule_name TOK_BINARY_OR)
        # The children list should alternate: operand, operator, operand, operator, ...
        # But we need to handle the case where operators might be mixed in
        operands = [child for child in children if isinstance(child, Expression)]
        operators = [child for child in children if hasattr(child, 'rule_name') and child.rule_name == 'TOK_BINARY_OR']
        
        if len(operands) == 1:
            return operands[0]
        
        if len(operands) != len(operators) + 1:
            # Fallback: if structure is unexpected, just chain operands with bitwise or
            result = operands[0]
            for i in range(1, len(operands)):
                result = BitwiseOrOp(left=result, right=operands[i], position=self._get_node_position(node))
            return result
        
        result = operands[0]
        for i in range(len(operators)):
            if i + 1 < len(operands):
                result = BitwiseOrOp(left=result, right=operands[i + 1], position=self._get_node_position(node))
        
        return result
    
    def visit_prec_binary_and(self, node, children):
        # prec_binary_and rule: OneOrMore(prec_binary_shift, sep=TOK_BINARY_AND)
        # The node structure is: [prec_binary_shift, operator, prec_binary_shift, operator, ...]
        # Operators are NonTerminal nodes with rule_name TOK_BINARY_AND
        if len(children) == 1:
            return children[0]
        
        # Get raw node children to access operators
        try:
            node_children = list(node)
            result = children[0]
            operand_idx = 1  # Index into children list (operands only)
            
            for i in range(1, len(node_children), 2):  # Skip every other (operators)
                if i < len(node_children):
                    operator_node = node_children[i]
                    # Check the rule_name to determine the operator
                    if hasattr(operator_node, 'rule_name'):
                        operator_rule = operator_node.rule_name
                    else:
                        operator_rule = None
                    
                    if operand_idx < len(children):
                        right_operand = children[operand_idx]
                        if operator_rule == 'TOK_BINARY_AND':
                            result = BitwiseAndOp(left=result, right=right_operand, position=self._get_node_position(node))
                        else:
                            # Default to bitwise and if unknown operator (shouldn't happen for prec_binary_and)
                            result = BitwiseAndOp(left=result, right=right_operand, position=self._get_node_position(node))
                        operand_idx += 1
        except (TypeError, AttributeError, IndexError):
            # Fallback: if we can't access raw children, default to bitwise and
            result = children[0]
            for i in range(1, len(children)):
                result = BitwiseAndOp(left=result, right=children[i], position=self._get_node_position(node))
        
        return result
    
    def visit_prec_binary_shift(self, node, children):
        # prec_binary_shift rule: OneOrMore(prec_addition, sep=[TOK_BINARY_SHIFT_LEFT, TOK_BINARY_SHIFT_RIGHT])
        # The node structure is: [prec_addition, operator, prec_addition, operator, ...]
        # Operators are NonTerminal nodes with rule_name TOK_BINARY_SHIFT_LEFT or TOK_BINARY_SHIFT_RIGHT
        if len(children) == 1:
            return children[0]
        
        # Get raw node children to access operators
        try:
            node_children = list(node)
            result = children[0]
            operand_idx = 1  # Index into children list (operands only)
            
            for i in range(1, len(node_children), 2):  # Skip every other (operators)
                if i < len(node_children):
                    operator_node = node_children[i]
                    if hasattr(operator_node, 'rule_name'):
                        operator_rule = operator_node.rule_name
                    else:
                        operator_rule = None
                    
                    if operand_idx < len(children):
                        right_operand = children[operand_idx]
                        if operator_rule == 'TOK_BINARY_SHIFT_LEFT':
                            result = BitwiseShiftLeftOp(left=result, right=right_operand, position=self._get_node_position(node))
                        elif operator_rule == 'TOK_BINARY_SHIFT_RIGHT':
                            result = BitwiseShiftRightOp(left=result, right=right_operand, position=self._get_node_position(node))
                        else:
                            # Default to shift left if unknown operator
                            result = BitwiseShiftLeftOp(left=result, right=right_operand, position=self._get_node_position(node))
                        operand_idx += 1
        except (TypeError, AttributeError, IndexError):
            # Fallback: if we can't access raw children, default to shift left
            result = children[0]
            for i in range(1, len(children)):
                result = BitwiseShiftLeftOp(left=result, right=children[i], position=self._get_node_position(node))
        
        return result
    
    def visit_prec_addition(self, node, children):
        # prec_addition rule: OneOrMore(prec_multiplication, sep=['+', '-'])
        # The children list contains: operands (Expression AST nodes) and operators (Terminal nodes with values '+', '-')
        # Operators are Terminal nodes passed through from _visit_node
        if len(children) == 1:
            return children[0]
        
        # Separate operands (Expression AST nodes) from operators (Terminal nodes with values '+', '-')
        operands = [child for child in children if isinstance(child, Expression)]
        operators = [child for child in children if not isinstance(child, Expression) and not isinstance(child, ASTNode)]
        
        if len(operands) == 1:
            return operands[0]
        
        if len(operands) != len(operators) + 1:
            # Fallback: if structure is unexpected, just chain operands with addition
            result = operands[0]
            for i in range(1, len(operands)):
                result = AdditionOp(left=result, right=operands[i], position=self._get_node_position(node))
            return result
        
        result = operands[0]
        for i in range(len(operators)):
            if i + 1 < len(operands):
                operator = operators[i] if isinstance(operators[i], str) else (getattr(operators[i], 'value', operators[i]) if hasattr(operators[i], 'value') else str(operators[i]))
                right_operand = operands[i + 1]
                if operator == '+':
                    result = AdditionOp(left=result, right=right_operand, position=self._get_node_position(node))
                elif operator == '-':
                    result = SubtractionOp(left=result, right=right_operand, position=self._get_node_position(node))
                else:
                    # Default to addition if unknown operator
                    result = AdditionOp(left=result, right=right_operand, position=self._get_node_position(node))
        
        return result
    
    def visit_prec_multiplication(self, node, children):
        # prec_multiplication rule: OneOrMore(prec_unary, sep=['*', '/', '%'])
        # The children list contains: operands (Expression AST nodes) and operators (Terminal nodes with values '*', '/', '%')
        # Operators are Terminal nodes passed through from _visit_node
        if len(children) == 1:
            return children[0]
        
        # Separate operands (Expression AST nodes) from operators (Terminal nodes with values '*', '/', '%')
        operands = [child for child in children if isinstance(child, Expression)]
        operators = [child for child in children if not isinstance(child, Expression) and not isinstance(child, ASTNode)]
        
        if len(operands) == 1:
            return operands[0]
        
        if len(operands) != len(operators) + 1:
            # Fallback: if structure is unexpected, just chain operands with multiplication
            result = operands[0]
            for i in range(1, len(operands)):
                result = MultiplicationOp(left=result, right=operands[i], position=self._get_node_position(node))
            return result
        
        result = operands[0]
        for i in range(len(operators)):
            if i + 1 < len(operands):
                operator = operators[i] if isinstance(operators[i], str) else (getattr(operators[i], 'value', operators[i]) if hasattr(operators[i], 'value') else str(operators[i]))
                right_operand = operands[i + 1]
                if operator == '*':
                    result = MultiplicationOp(left=result, right=right_operand, position=self._get_node_position(node))
                elif operator == '/':
                    result = DivisionOp(left=result, right=right_operand, position=self._get_node_position(node))
                elif operator == '%':
                    result = ModuloOp(left=result, right=right_operand, position=self._get_node_position(node))
                else:
                    # Default to multiplication if unknown operator
                    result = MultiplicationOp(left=result, right=right_operand, position=self._get_node_position(node))
        
        return result
    
    def visit_prec_unary(self, node, children):
        # prec_unary rule: (ZeroOrMore(['+', '-', TOK_LOGICAL_NOT, TOK_BINARY_NOT]), prec_exponent)
        # The node structure is: [operator1, operator2, ..., prec_exponent]
        # But Terminal nodes (operators) return None from _visit_node, so we need to access raw children
        exprs = [child for child in children if isinstance(child, Expression)]
        if not exprs:
            raise ValueError("prec_unary should have an Expression child")
        result = exprs[0]
        
        # Get raw node children to access operators
        try:
            node_children = list(node)
            # Operators are all Terminal nodes before the last child (which is prec_exponent)
            ops = []
            for i in range(len(node_children) - 1):  # All but the last child are operators
                operator_node = node_children[i]
                if hasattr(operator_node, 'value'):
                    op = operator_node.value
                elif hasattr(operator_node, 'rule_name'):
                    # Handle TOK_LOGICAL_NOT and TOK_BINARY_NOT
                    if operator_node.rule_name == 'TOK_LOGICAL_NOT':
                        op = '!'
                    elif operator_node.rule_name == 'TOK_BINARY_NOT':
                        op = '~'
                    else:
                        op = str(operator_node)
                else:
                    op = str(operator_node)
                ops.append(op)
            
            # Apply operators right-to-left (last operator first)
            for op in reversed(ops):
                if op == '-':
                    result = UnaryMinusOp(expr=result, position=self._get_node_position(node))
                elif op == '!':
                    result = LogicalNotOp(expr=result, position=self._get_node_position(node))
                elif op == '~':
                    result = BitwiseNotOp(expr=result, position=self._get_node_position(node))
                # '+' does nothing (unary plus)
        except (TypeError, AttributeError, IndexError):
            # Fallback: try to find operators in children (old behavior)
            ops = [child for child in children if isinstance(child, str) and child in ['+', '-', '!', '~']]
            for op in reversed(ops):
                if op == '-':
                    result = UnaryMinusOp(expr=result, position=self._get_node_position(node))
                elif op == '!':
                    result = LogicalNotOp(expr=result, position=self._get_node_position(node))
                elif op == '~':
                    result = BitwiseNotOp(expr=result, position=self._get_node_position(node))
        
        return result
    
    def visit_prec_exponent(self, node, children):
        # prec_exponent rule: [(prec_call, '^', prec_unary), prec_call]
        if len(children) == 1:
            return children[0]
        # Right-associative: a^b^c = a^(b^c)
        result = children[-1]
        for i in range(len(children) - 2, -1, -1):
            result = ExponentOp(left=children[i], right=result, position=self._get_node_position(node))
        return result
    
    def visit_prec_call(self, node, children):
        # prec_call rule: (primary, ZeroOrMore([call_expr, lookup_expr, member_expr]))
        if len(children) == 1:
            child = children[0]
            if isinstance(child, Expression):
                return child
            return child  # Fallback
        result = children[0]
        if not isinstance(result, Expression):
            # If first child is not an Expression, we can't proceed
            return result
        # Process suffixes left-to-right
        # The children after the first are tuples: ('call', args), ('index', expr), or ('member', identifier)
        for i in range(1, len(children)):
            child = children[i]
            if isinstance(child, tuple) and len(child) == 2:
                op_type, op_value = child
                if op_type == 'call':
                    arguments = op_value if isinstance(op_value, list) else [op_value] if isinstance(op_value, Argument) else []
                    result = PrimaryCall(left=result, arguments=arguments, position=self._get_node_position(node))
                elif op_type == 'index':
                    if isinstance(op_value, Expression):
                        result = PrimaryIndex(left=result, index=op_value, position=self._get_node_position(node))
                elif op_type == 'member':
                    if isinstance(op_value, Identifier):
                        result = PrimaryMember(left=result, member=op_value, position=self._get_node_position(node))
            elif isinstance(child, Expression):
                # Fallback: if it's already an Expression, use it directly
                result = child
        return result
    
    def visit_call_expr(self, node, children):
        # call_expr rule: ('(', arguments, ')')
        # children: list of Argument objects (from arguments rule)
        arguments = [child for child in children if isinstance(child, Argument)]
        # Return tuple marker for visit_prec_call
        return ('call', arguments)
    
    def visit_lookup_expr(self, node, children):
        # lookup_expr rule: ('[', expr, ']')
        expr = [child for child in children if isinstance(child, Expression)]
        if not expr:
            raise ValueError("lookup_expr should have an Expression child")
        # Return tuple marker for visit_prec_call
        return ('index', expr[0])
    
    def visit_member_expr(self, node, children):
        # member_expr rule: ('.', TOK_ID)
        # children: [Terminal ('.'), Identifier (from TOK_ID)]
        # Terminal nodes are now passed through, so we need to filter them out
        
        # Find the Identifier (should be the only AST node in children)
        identifier = None
        for child in children:
            if isinstance(child, Identifier):
                identifier = child
                break
        
        if identifier is None:
            # Fallback: try to extract name from children
            name_str = None
            for child in children:
                if isinstance(child, str) and child != '.':
                    name_str = child
                    break
                elif isinstance(child, Identifier):
                    name_str = child.name
                    break
            
            if name_str is None:
                raise ValueError("member_expr should have an Identifier child")
            identifier = Identifier(name=name_str, position=self._get_node_position(node))
        
        # Return tuple marker for visit_prec_call
        return ('member', identifier)
    
    def visit_primary(self, node, children):
        # primary rule handles multiple alternatives:
        # - ('(', expr, ')') -> just return the expr (already processed), filtering out '(' and ')'
        # - range_expr -> handled by visit_range_expr (returns RangeLiteral)
        # - vector_expr -> handled by visit_vector_expr (returns ListComprehension)
        # - TOK_UNDEF -> handled by visit_TOK_UNDEF (returns UndefinedLiteral)
        # - TOK_TRUE -> handled by visit_TOK_TRUE (returns BooleanLiteral)
        # - TOK_FALSE -> handled by visit_TOK_FALSE (returns BooleanLiteral)
        # - TOK_STRING -> handled by visit_TOK_STRING (returns StringLiteral)
        # - TOK_NUMBER -> handled by visit_TOK_NUMBER (returns NumberLiteral)
        # - TOK_ID -> handled by visit_TOK_ID (returns Identifier)
        # All children are already processed by their respective visitor methods
        # Filter out Terminal nodes (like '(' and ')') and return the first Expression/AST node
        if not children:
            raise ValueError("primary should have at least one child")
        
        # Filter out Terminal nodes (strings like '(', ')', '[', ']', etc.)
        ast_children = [child for child in children if isinstance(child, ASTNode)]
        if ast_children:
            return ast_children[0]
        
        # Fallback: return first child if no AST nodes found
        return children[0]
    
    def visit_range_expr(self, node, children):
        # range_expr rule: ('[', expr, ':', expr, Optional(':', expr), ']')
        # Children will be: expr, ':', expr, optional ':', optional expr
        # Extract expressions, filtering out ':' separators
        exprs = [child for child in children if isinstance(child, Expression)]
        if len(exprs) < 2:
            raise ValueError("range_expr should have at least 2 Expression children (start and end)")
        start = exprs[0]
        end = exprs[1]
        # Step is optional - if present, use it; otherwise default to 1.0
        step = exprs[2] if len(exprs) > 2 else NumberLiteral(val=1.0, position=self._get_node_position(node))
        return RangeLiteral(start=start, end=end, step=step, position=self._get_node_position(node))
    
    def visit_vector_expr(self, node, children):
        # vector_expr rule: ('[', vector_elements, Optional(TOK_COMMA), ']')
        # Children will be: vector_elements result (list), optional comma
        # visit_vector_elements returns a list of VectorElement or Expression
        elements = []
        for child in children:
            if isinstance(child, list):
                # vector_elements returns a list
                elements.extend([item for item in child if isinstance(item, (VectorElement, Expression))])
            elif isinstance(child, (VectorElement, Expression)):
                # Individual element (shouldn't happen, but handle it)
                elements.append(child)
        
        # ListComprehension expects list[VectorElement]
        # vector_element can be either listcomp_elements (VectorElement) or expr (Expression)
        # For simple vectors like [1, 2, 3], elements will be Expressions
        # For list comprehensions, elements will be VectorElements
        # We need to filter to only VectorElement types
        vector_elements_list = [elem for elem in elements if isinstance(elem, VectorElement)]
        
        # Note: If elements contains Expressions (simple vectors), they are filtered out.
        # This suggests that simple vectors might need a different AST representation,
        # or ListComprehension should accept both types. For now, we only include VectorElements.
        
        return ListComprehension(elements=vector_elements_list, position=self._get_node_position(node))
    
    def visit_funclit_def(self, node, children):
        # funclit_def rule: (TOK_FUNCTION, '(', parameters, ')', expr)
        # children: parameters list, expr
        params = [child for child in children if isinstance(child, ParameterDeclaration)]
        expr = [child for child in children if isinstance(child, Expression) and not isinstance(child, ParameterDeclaration)]
        if not expr:
            raise ValueError("funclit_def should have an Expression body")
        # FunctionLiteral needs arguments (list[Argument]), but we have parameters (list[ParameterDeclaration])
        # This seems like a mismatch in the AST definition - parameters should be used for function definition, not arguments
        # For now, create empty arguments list
        return FunctionLiteral(arguments=[], body=expr[0], position=self._get_node_position(node))
    
    def visit_vector_elements(self, node, children):
        # vector_elements rule: ZeroOrMore(vector_element, sep=TOK_COMMA)
        # Return list of VectorElement objects
        elements = [child for child in children if isinstance(child, (VectorElement, Expression))]
        return elements
    
    def visit_vector_element(self, node, children):
        # vector_element rule: [listcomp_elements, expr]
        # Return the first child (either a VectorElement from listcomp_elements, or an Expression)
        if not children:
            raise ValueError("vector_element should have at least one child")
        child = children[0]
        # If it's an Expression, wrap it appropriately
        # Actually, VectorElement is a base class, and Expression can be used directly in some contexts
        # For simplicity, return as-is
        return child
    
    def visit_listcomp_elements(self, node, children):
        # listcomp_elements rule: [('(', listcomp_elements, ')'), listcomp_let, listcomp_each, listcomp_for, listcomp_ifelse]
        # Return the first (and only) child
        if not children:
            raise ValueError("listcomp_elements should have at least one child")
        return children[0]
    
    def visit_listcomp_let(self, node, children):
        # listcomp_let rule: (TOK_LET, '(', assignments_expr, ')', listcomp_elements)
        assignments = [child for child in children if isinstance(child, Assignment)]
        # ListCompLet.body is Expression, but listcomp_elements returns VectorElement
        # Check the AST definition - it says body: Expression
        body = [child for child in children if isinstance(child, Expression) and not isinstance(child, Assignment)]
        if not body:
            # Try VectorElement as fallback (might need to check AST definition)
            vec_body = [child for child in children if isinstance(child, VectorElement) and not isinstance(child, Assignment)]
            if vec_body:
                # This is a type mismatch - ListCompLet expects Expression but we have VectorElement
                # For now, we'll need to check the actual AST definition
                raise ValueError(f"listcomp_let body type mismatch: ListCompLet expects Expression but got VectorElement")
            raise ValueError("listcomp_let should have a body")
        return ListCompLet(assignments=assignments, body=body[0], position=self._get_node_position(node))
    
    def visit_listcomp_each(self, node, children):
        # listcomp_each rule: (TOK_EACH, vector_element)
        body = [child for child in children if isinstance(child, VectorElement)]
        if not body:
            raise ValueError("listcomp_each should have a VectorElement body")
        return ListCompEach(body=body[0], position=self._get_node_position(node))
    
    def visit_listcomp_for(self, node, children):
        # listcomp_for rule: [(TOK_FOR, '(', assignments_expr, ';', expr, ';', assignments_expr, ')', vector_element), (TOK_FOR, '(', assignments_expr, ')', vector_element)]
        assignments = [child for child in children if isinstance(child, Assignment)]
        exprs = [child for child in children if isinstance(child, Expression) and not isinstance(child, Assignment)]
        body = [child for child in children if isinstance(child, VectorElement) and not isinstance(child, Assignment) and child not in exprs]
        if len(assignments) == 1 and len(exprs) == 0:
            # Simple for: for (assignments) body
            if not body:
                raise ValueError("listcomp_for should have a VectorElement body")
            return ListCompFor(assignments=assignments, body=body[0], position=self._get_node_position(node))
        elif len(assignments) == 2 and len(exprs) == 1:
            # C-style for: for (initial; condition; increment) body
            if not body:
                raise ValueError("listcomp_for should have a VectorElement body")
            return ListCompCStyleFor(initial=assignments[:1], condition=exprs[0], increment=assignments[1:], body=body[0], position=self._get_node_position(node))
        else:
            raise ValueError(f"listcomp_for has unexpected structure: {len(assignments)} assignments, {len(exprs)} expressions")
    
    def visit_listcomp_ifelse(self, node, children):
        # listcomp_ifelse rule: [(TOK_IF, '(', expr, ')', vector_element, TOK_ELSE, vector_element), (TOK_IF, '(', expr, ')', vector_element)]
        exprs = [child for child in children if isinstance(child, Expression)]
        vectors = [child for child in children if isinstance(child, VectorElement) and child not in exprs]
        if len(exprs) != 1:
            raise ValueError("listcomp_ifelse should have exactly one condition expression")
        condition = exprs[0]
        if len(vectors) == 2:
            return ListCompIfElse(condition=condition, true_expr=vectors[0], false_expr=vectors[1], position=self._get_node_position(node))
        elif len(vectors) == 1:
            return ListCompIf(condition=condition, true_expr=vectors[0], position=self._get_node_position(node))
        else:
            raise ValueError(f"listcomp_ifelse has unexpected structure: {len(vectors)} vector elements")
    
    def visit_modular_call(self, node, children):
        # modular_call rule: (TOK_ID, "(", arguments, ")", child_statement)
        # children: identifier, arguments list, module instantiations list
        name = children[0] if isinstance(children[0], Identifier) else Identifier(name=children[0], position=self._get_node_position(node))
        arguments = [child for child in children if isinstance(child, Argument)]
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        return ModularCall(name=name, arguments=arguments, children=mods, position=self._get_node_position(node))
    
    def visit_modular_for(self, node, children):
        # modular_for rule: [(TOK_FOR, "(", assignments_expr, ")", child_statement), (TOK_FOR, "(", assignments_expr, ";", expr, ";", assignments_expr, ")", child_statement)]
        assignments = [child for child in children if isinstance(child, Assignment)]
        exprs = [child for child in children if isinstance(child, Expression) and not isinstance(child, Assignment)]
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        if len(assignments) == 1 and len(exprs) == 0:
            # Simple for
            if not mods:
                raise ValueError("modular_for should have a ModuleInstantiation body")
            return ModularFor(assignments=assignments, body=mods[0], position=self._get_node_position(node))
        elif len(assignments) == 2 and len(exprs) == 1:
            # C-style for
            if not mods:
                raise ValueError("modular_for should have a ModuleInstantiation body")
            return ModularCLikeFor(initial=assignments[:1], condition=exprs[0], increment=assignments[1:], body=mods[0], position=self._get_node_position(node))
        else:
            raise ValueError(f"modular_for has unexpected structure")
    
    def visit_modular_intersection_for(self, node, children):
        # modular_intersection_for rule: (TOK_INTERSECTION_FOR, "(", assignments_expr, ")", child_statement)
        assignments = [child for child in children if isinstance(child, Assignment)]
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        if not mods:
            raise ValueError("modular_intersection_for should have a ModuleInstantiation body")
        return ModularIntersectionFor(assignments=assignments, body=mods[0], position=self._get_node_position(node))
    
    def visit_modular_let(self, node, children):
        # modular_let rule: (TOK_LET, "(", assignments_expr, ")", child_statement)
        assignments = [child for child in children if isinstance(child, Assignment)]
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        return ModularLet(assignments=assignments, children=mods, position=self._get_node_position(node))
    
    def visit_modular_echo(self, node, children):
        # modular_echo rule: (TOK_ECHO, "(", arguments, ")", child_statement)
        arguments = [child for child in children if isinstance(child, Argument)]
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        return ModularEcho(arguments=arguments, children=mods, position=self._get_node_position(node))
    
    def visit_modular_assert(self, node, children):
        # modular_assert rule: (TOK_ASSERT, "(", arguments, ")", child_statement)
        arguments = [child for child in children if isinstance(child, Argument)]
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        return ModularAssert(arguments=arguments, children=mods, position=self._get_node_position(node))
    
    def visit_ifelse_statement(self, node, children):
        # ifelse_statement rule: [(TOK_IF, '(', expr, ')', child_statement, TOK_ELSE, child_statement), (TOK_IF, '(', expr, ')', child_statement)]
        exprs = [child for child in children if isinstance(child, Expression)]
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        if len(exprs) != 1:
            raise ValueError("ifelse_statement should have exactly one condition expression")
        condition = exprs[0]
        if len(mods) == 2:
            return ModularIfElse(condition=condition, true_branch=mods[0], false_branch=mods[1], position=self._get_node_position(node))
        elif len(mods) == 1:
            return ModularIf(condition=condition, true_branch=mods[0], position=self._get_node_position(node))
        else:
            raise ValueError(f"ifelse_statement has unexpected structure: {len(mods)} module instantiations")
    
    def visit_modifier_show_only(self, node, children):
        # modifier_show_only rule: ('!', module_instantiation)
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        if not mods:
            raise ValueError("modifier_show_only should have a ModuleInstantiation child")
        return ModularModifierShowOnly(child=mods[0], position=self._get_node_position(node))
    
    def visit_modifier_highlight(self, node, children):
        # modifier_highlight rule: ('#', module_instantiation)
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        if not mods:
            raise ValueError("modifier_highlight should have a ModuleInstantiation child")
        return ModularModifierHighlight(child=mods[0], position=self._get_node_position(node))
    
    def visit_modifier_background(self, node, children):
        # modifier_background rule: ('%', module_instantiation)
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        if not mods:
            raise ValueError("modifier_background should have a ModuleInstantiation child")
        return ModularModifierBackground(child=mods[0], position=self._get_node_position(node))
    
    def visit_modifier_disable(self, node, children):
        # modifier_disable rule: ('*', module_instantiation)
        mods = [child for child in children if isinstance(child, ModuleInstantiation)]
        if not mods:
            raise ValueError("modifier_disable should have a ModuleInstantiation child")
        return ModularModifierDisable(child=mods[0], position=self._get_node_position(node))
    
    def visit_assignment(self, node, children):
        # assignment rule: (TOK_ID, TOK_ASSIGN, expr, ';')
        # Similar to assignment_expr but with semicolon
        name = children[0] if isinstance(children[0], Identifier) else Identifier(name=children[0], position=self._get_node_position(node))
        expr = [child for child in children[1:] if isinstance(child, Expression)]
        if not expr:
            raise ValueError("assignment should have an Expression child")
        return Assignment(name=name, expr=expr[0], position=self._get_node_position(node))
    
    def visit_comment_line(self, node, children):
        # comment_line rule: _(r'//.*?$', str_repr='comment')
        # The regex matches the entire comment including //, so node.value contains the full match
        # Follow the same pattern as other terminal nodes
        text = children[-1] if children else (node.value if hasattr(node, 'value') else "")
        # Remove the // prefix if present
        if text.startswith("//"):
            text = text[2:]
        return CommentLine(text=text, position=self._get_node_position(node))
    
    def visit_comment_multi(self, node, children):
        # comment_multi rule: _(r'(?ms)/\*.*?\*/', str_repr='comment')
        # The regex matches the entire comment including /* and */, so node.value contains the full match
        # Follow the same pattern as other terminal nodes
        text = children[-1] if children else (node.value if hasattr(node, 'value') else "")
        # Remove the /* prefix and */ suffix if present
        if text.startswith("/*"):
            text = text[2:]
        if text.endswith("*/"):
            text = text[:-2]
        return CommentSpan(text=text, position=self._get_node_position(node))
    
    def visit_comment(self, node, children):
        # comment rule: [comment_line, comment_multi]
        # This is a dispatcher - just return the first (and only) child
        if not children:
            raise ValueError("comment should have at least one child")
        return children[0]
    
    def visit_statement(self, node, children):
        # statement rule: [";", ('{', ZeroOrMore(statement), '}'), module_definition, function_definition, module_instantiation, assignment]
        # This is a dispatcher - children are already processed by their respective visitor methods
        # For semicolon (';'), there are no children, so we return None or skip
        # For block ('{', ZeroOrMore(statement), '}'), children contains: [None (from '{'), statement1, statement2, ..., None (from '}')]
        # For others, we get the appropriate AST node
        if not children:
            # Empty statement (semicolon)
            return None
        
        # Check if this is a block (starts and ends with None from '{' and '}')
        # Blocks have multiple children (statements inside)
        if len(children) > 1:
            # Filter out None values (from '{' and '}') and return the list of statements
            statements = [child for child in children if child is not None]
            # If we have multiple statements, return them as a list
            # Otherwise, return the single statement
            return statements if len(statements) > 1 else (statements[0] if statements else None)
        
        # Return the first child (module_definition, function_definition, module_instantiation, assignment)
        return children[0]
    
    def visit_module_instantiation(self, node, children):
        # module_instantiation rule: [modifier_show_only, modifier_highlight, modifier_background, modifier_disable, ifelse_statement, single_module_instantiation]
        # This is a dispatcher - children are already processed by their respective visitor methods
        if not children:
            raise ValueError("module_instantiation should have at least one child")
        # Return the first (and only) child, which is already the appropriate ModuleInstantiation AST node
        return children[0]
    
    def visit_single_module_instantiation(self, node, children):
        # single_module_instantiation rule: [modular_for, modular_intersection_for, modular_let, modular_assert, modular_echo, modular_call]
        # This is a dispatcher - children are already processed by their respective visitor methods
        if not children:
            raise ValueError("single_module_instantiation should have at least one child")
        # Return the first (and only) child, which is already the appropriate ModuleInstantiation AST node
        return children[0]
    
    def visit_child_statement(self, node, children):
        # child_statement rule: [';', ('{', ZeroOrMore([assignment, child_statement]), '}'), module_instantiation]
        # This is a dispatcher - children are already processed by their respective visitor methods
        # For semicolon (';'), there are no children, so we return None
        # For block ('{', ...), we might get a list of statements
        # For module_instantiation, we get the ModuleInstantiation AST node
        if not children:
            # Empty statement (semicolon)
            return None
        # Return the first child (module_instantiation or block)
        return children[0]
    
    def visit_expr(self, node, children) -> Expression:
        # expr rule: [let_expr, assert_expr, echo_expr, funclit_def, ternary_expr, prec_logical_or]
        # This is a dispatcher - children are already processed by their respective visitor methods
        if not children:
            raise ValueError("expr should have at least one child")
        # Return the first (and only) child, which is already the appropriate Expression AST node
        return children[0]
    
    def visit_openscad_language(self, node, children) -> list[ASTNode]:
        # openscad_language rule: (ZeroOrMore([use_statement, include_statement, statement]), EOF)
        # Collect all statements, filtering out EOF (Terminal nodes) and None values
        statements = [child for child in children if child is not None and isinstance(child, ASTNode)]
        return statements


def parse_ast(parser, code, file="") -> list[ASTNode] | None:
    """Parse code and return AST nodes using ASTBuilderVisitor.
    
    This is the main public API for converting OpenSCAD code to an AST.
    
    Args:
        parser: An Arpeggio parser instance (from getOpenSCADParser())
        code: The OpenSCAD code string to parse
        file: Optional file path for source location tracking
        
    Returns:
        The root AST node (or list of AST nodes for the root level)
    """
    parse_tree = parser.parse(code)
    visitor = ASTBuilderVisitor(parser, file=file)
    return visitor.visit_parse_tree(parse_tree)


def getASTfromString(code: str) -> ASTNode | list[ASTNode] | None:
    """
    Parse OpenSCAD source code from a string and return its abstract syntax tree (AST).

    This function creates a new OpenSCAD parser instance, parses the provided code string,
    and returns the resulting AST (or list of AST nodes) for further analysis or processing.

    Args:
        code (str): The OpenSCAD source code to be parsed.

    Returns:
        ASTNode | list[ASTNode] | None: The AST representation of the OpenSCAD source code.
            Returns None if the code is empty or does not contain valid statements.

    Example:
        ast = getASTfromString("cube([1,2,3]);")
    """
    parser = getOpenSCADParser(reduce_tree=False)
    ast = parse_ast(parser, code)
    return ast


# Module-level cache for AST trees
# Key: absolute file path (str)
# Value: tuple of (AST nodes, modification timestamp)
_ast_cache: dict[str, tuple[list[ASTNode] | None, float]] = {}


def clear_ast_cache():
    """Clear the in-memory AST cache.
    
    This function removes all cached AST trees, forcing all subsequent
    calls to getASTfromFile() to re-parse files.
    
    Example:
        clear_ast_cache()  # Clear all cached ASTs
    """
    _ast_cache.clear()


def getASTfromFile(file: str) -> list[ASTNode] | None:
    """
    Parse an OpenSCAD source file and return its corresponding abstract syntax tree (AST).

    This function reads the contents of the provided OpenSCAD file, parses it using the OpenSCAD parser,
    and returns the resulting AST (or list of AST nodes) for further analysis or processing.
    
    The function caches AST trees in memory. Cache entries are automatically invalidated
    if the file's modification timestamp changes, ensuring that updated files are re-parsed.

    Args:
        file (str): The OpenSCAD source file to be parsed.

    Returns:
        list[ASTNode] | None: The AST representation of the OpenSCAD source file.
            Returns None if the file is empty or does not contain valid statements.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        Exception: If there is an error while reading the file.

    Example:
        ast = getASTfromFile("my_model.scad")
    """
    # Get absolute path for consistent cache keys
    file_path = os.path.abspath(file)
    
    # Check if file exists and get its modification time
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file} not found")
    
    current_mtime = os.path.getmtime(file_path)
    
    # Check cache
    if file_path in _ast_cache:
        cached_ast, cached_mtime = _ast_cache[file_path]
        # If file hasn't been modified, return cached AST
        if cached_mtime == current_mtime:
            return cached_ast
        # Otherwise, invalidate the cache entry
        del _ast_cache[file_path]
    
    # Parse the file
    try:
        with open(file_path, 'r') as f:
            code = f.read()
    except Exception as e:
        raise Exception(f"Error reading file {file}: {e}")
    
    parser = getOpenSCADParser(reduce_tree=False)
    ast = parse_ast(parser, code, file_path)
    
    # Cache the result with current modification time
    _ast_cache[file_path] = (ast, current_mtime)
    
    return ast


def _find_library_file(currfile: str, libfile: str) -> Optional[str]:
    """Find a library file using OpenSCAD's search path rules.
    
    Searches for the library file in the following order:
    1. Directory of the current file (if currfile is provided)
    2. Directories specified in OPENSCADPATH environment variable
    3. Platform-specific default library directories
    
    Args:
        currfile: Full path to the current OpenSCAD file (can be empty string)
        libfile: Partial or full path to the library file to find
        
    Returns:
        Full path to the found library file, or None if not found
    """
    dirs = []
    
    # Add directory of current file if provided
    if currfile:
        dirs.append(os.path.dirname(os.path.abspath(currfile)))
    
    # Determine path separator and default path based on platform
    pathsep = ":"
    dflt_path = ""
    system = platform.system()
    
    if system == "Windows":
        dflt_path = os.path.join(os.path.expanduser("~"), "Documents", "OpenSCAD", "libraries")
        pathsep = ";"
    elif system == "Darwin":
        dflt_path = os.path.expanduser("~/Documents/OpenSCAD/libraries")
    elif system == "Linux":
        dflt_path = os.path.expanduser("~/.local/share/OpenSCAD/libraries")
    
    # Get OPENSCADPATH from environment or use default
    env = os.getenv("OPENSCADPATH", dflt_path)
    if env:
        for path in env.split(pathsep):
            expanded_path = os.path.expandvars(path)
            if expanded_path:
                dirs.append(expanded_path)
    
    # Search for the file in each directory
    for d in dirs:
        test_file = os.path.join(d, libfile)
        if os.path.isfile(test_file):
            return test_file
    
    return None


def getASTfromLibraryFile(currfile: str, libfile: str) -> tuple[list[ASTNode] | None, str]:
    """
    Find and parse an OpenSCAD library file using OpenSCAD's search path rules,
    and return both the AST and absolute path to the file.

    This function searches for the library file in the following order:
    1. Directory of the current file (if currfile is provided)
    2. Directories specified in OPENSCADPATH environment variable
    3. Platform-specific default library directories:
       - Windows: ~/Documents/OpenSCAD/libraries
       - macOS: ~/Documents/OpenSCAD/libraries
       - Linux: ~/.local/share/OpenSCAD/libraries

    Once found, the file is parsed using getASTfromFile(), which includes
    caching support.

    Args:
        currfile: Full path to the current OpenSCAD file that wants to include/use
                  the library file. Can be empty string if not available.
        libfile: Partial or full path to the library file to find and parse.
                 This is typically the path specified in a 'use' or 'include' statement.

    Returns:
        tuple[list[ASTNode] | None, str]: The AST representation of the library file
            and the absolute path of the file parsed. The list is None if empty or not valid.
    
    Raises:
        FileNotFoundError: If the library file cannot be found in any search path.
        Exception: If there is an error while reading or parsing the file.

    Example:
        # From a file at /path/to/main.scad that includes "utils/math.scad"
        ast, path = getASTfromLibraryFile("/path/to/main.scad", "utils/math.scad")
        
        # Or without current file context
        ast, path = getASTfromLibraryFile("", "MCAD/boxes.scad")
    """
    found_file = _find_library_file(currfile, libfile)

    if found_file is None:
        raise FileNotFoundError(
            f"Library file '{libfile}' not found in search paths. "
            f"Searched in: current file directory, OPENSCADPATH, and platform default paths."
        )

    # Use getASTfromFile() which includes caching
    ast = getASTfromFile(found_file)
    return ast, os.path.abspath(found_file)
