from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .builder import Position


# --- AST nodes classes. ---

@dataclass
class ASTNode(object):
    """Base class for all AST nodes.
    
    All AST nodes in the OpenSCAD parser inherit from this class. It provides
    a common interface for source position tracking and string representation.
    
    Attributes:
        position: The source position of this node in the original OpenSCAD code.
    """
    position: "Position"

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

    def __repr__(self):
        return f"Identifier('{self.name}')"


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
class ListCompCFor(VectorElement):
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
class ModularCFor(ModuleInstantiation):
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
class ModularIntersectionCFor(ModuleInstantiation):
    """Represents an intersection_for C-style loop module instantiation.

    Similar to a C-style for loop, but computes the intersection of all
    iterations rather than the union. Used for creating complex intersections
    that use explicit initialization, condition, and increment.

    Examples:
        intersection_for(i = 0; i < 3; i = i + 1) rotate([0,0,i*90]) cube(10);

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
        return (
            f"intersection_for ("
            f"{'; '.join(str(a) for a in self.initial)}; "
            f"{self.condition}; "
            f"{', '.join(str(a) for a in self.increment)}"
            f") {self.body}"
        )


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


