# OpenSCAD Pretty-Printing Standards

This document specifies the formatting rules applied by `to_openscad()` when converting an AST back to OpenSCAD source code. It serves as the reference for anyone extending the pretty-printer or writing tests against its output.

## Table of Contents

1. [Overview](#1-overview)
2. [Indentation](#2-indentation)
3. [Blank Line Separation](#3-blank-line-separation)
4. [Assignments and Variables](#4-assignments-and-variables)
5. [Expressions](#5-expressions)
6. [Parameter Formatting](#6-parameter-formatting)
7. [Function Declarations](#7-function-declarations)
8. [Module Declarations](#8-module-declarations)
9. [Module Instantiations](#9-module-instantiations)
10. [Control Flow](#10-control-flow)
11. [Modifiers](#11-modifiers)
12. [Comments](#12-comments)
13. [Use and Include Statements](#13-use-and-include-statements)

---

## 1. Overview

The entry point is `to_openscad(nodes, indent_width=4)` in `openscad_parser.ast.pretty_print`. It accepts a list of top-level AST nodes and returns a formatted string. The default indentation width is 4 spaces.

```python
from openscad_parser.ast import getASTfromString, to_openscad

ast = getASTfromString("x=1;")
print(to_openscad(ast))   # → "x = 1;"
```

---

## 2. Indentation

- Each nesting level adds `indent_width` spaces (default: 4).
- Indentation uses spaces only — no tabs.
- The `indent_width` parameter is threaded through every formatting call, so custom widths apply uniformly.

```
module outer() {
    module inner() {
        cube(1);
    }
}
```

---

## 3. Blank Line Separation

A blank line is inserted before and after every `function` or `module` declaration. Simple assignments and statements are not separated by blank lines.

```
x = 1;
y = 2;

function area(w, h) = w * h;

module box(w, h) {
    cube([w, h, 1]);
}

z = 3;
```

Specifically, a blank line is emitted whenever the current node or the previous node is a `FunctionDeclaration` or `ModuleDeclaration`.

---

## 4. Assignments and Variables

```
name = expression;
```

- One space on each side of `=`.
- Terminated with `;`.
- Multi-line expressions (see [§5](#5-expressions)) extend the statement across multiple lines; the `;` closes the last line.

---

## 5. Expressions

Most expressions are rendered inline using their `__str__` method. The following expression types receive special multiline treatment.

### Ternary Expressions

A ternary expression `condition ? true_expr : false_expr` is always formatted across three lines. The `?` and `:` operators are placed at the start of their lines, indented 2 spaces relative to the current statement's indentation level.

```
x = condition
  ? true_expr
  : false_expr;
```

Inside an indented block (e.g., inside a module body at indent 4):

```
    x = condition
      ? true_expr
      : false_expr;
```

Nested ternaries indent by an additional 2 spaces per level:

```
x = condition1
  ? true_expr
  : condition2
    ? true_expr2
    : false_expr2;
```

This rule applies uniformly to ternaries in assignment right-hand sides and function declaration bodies.

### Assert and Echo Expressions

`assert(...)` and `echo(...)` used as expressions each appear on their own line, with the body expression following at the same indentation. Multiple assert/echo prefixes chain naturally.

```
function f(x) =
    assert(x > 0)
    echo("x =", x)
    x * 2;
```

### Let Expressions

`let(...)` used as an expression always places its body on the next line at the same indentation as the `let`.

**Inline** — zero or one assignment, and that assignment's value fits on a single line:

```
function f(x) =
    let(y = x * 2)
    y + 1;
```

**Block** — two or more assignments, or any single assignment whose value is multiline (e.g. a ternary): `let(` opens, each assignment on its own line indented one level, `)` closes at the original indent:

```
function f(a, b) =
    let(
        x = a * 2,
        y = b + 1
    )
    x + y;

function f(x) =
    let(
        y = x > 0
          ? x
          : -x
    )
    y + 1;
```

This same inline/block rule applies to `let()` inside `let()` module calls and inside list comprehensions.

### Long Function Call Expressions

A function call expression (e.g. `foo(a, b, c)` appearing inside an assignment or larger expression) is formatted across multiple lines when the call's length plus the current indentation exceeds 100 characters. Each argument goes on its own line indented one level, with the closing `)` at the original indent.

```
x = some_function(
    very_long_argument_one,
    very_long_argument_two,
    very_long_argument_three
);
```

### List Comprehensions

A list comprehension is rendered inline when its total length (plus indentation) fits within 100 characters. When it exceeds the limit, `[` opens on the first line, each element goes on its own line indented one level, and `]` closes at the original indent.

```
x = [
    element_one,
    element_two,
    element_three
];
```

**`for` elements** within a multiline comprehension always place the body on the next line, indented one level:

```
x = [
    for (variable = [start:step:end])
        body_expression
];
```

If the `for (assignments)` header itself exceeds 100 characters, assignments are formatted one per line with `)` on its own line at the `for` indent:

```
x = [
    for (
        very_long_variable_alpha = [start:end],
        very_long_variable_beta = [0:10]
    )
        body_expression
];
```

Nested `for` loops indent recursively:

```
x = [
    for (i = [0:n])
        for (j = [0:m])
            i + j
];
```

C-style `for` loops (`for (init; cond; incr)`) also place the body on the next line but keep the three-part header on one line.

**`let` elements** within a comprehension follow the same inline/block rule as let expressions. If any assignment value is multiline, the whole comprehension is forced to expand and the `let` uses the block format:

```
x = [
    let(
        y = condition
          ? value_a
          : value_b
    )
    y + 1
];
```

A `let` with only simple assignments stays inline and does not force comprehension expansion:

```
x = [let(y = 2) y + 1];
```

### Boolean Literals

`true` and `false` are always written in lowercase, matching OpenSCAD syntax.

```
x = true;
y = false;
cube(size=10, center=true);
```

### Operator Precedence and Parentheses

The pretty-printer re-inserts parentheses wherever they are needed to preserve the evaluation order encoded in the AST. Redundant parentheses present in the original source are dropped.

```
// source:   x = (3+5)/2;
// printed:  x = (3 + 5) / 2;

// source:   x = a - (b - c);
// printed:  x = a - (b - c);   // parens needed: subtraction is left-associative

// source:   x = a + b * c;
// printed:  x = a + b * c;     // no parens needed: * already binds tighter

// source:   x = (a || b) && c;
// printed:  x = (a || b) && c; // parens needed: || has lower precedence than &&
```

The precedence table (low → high):

| Level | Operators |
|-------|-----------|
| 10 | `?:` (ternary) |
| 20 | `\|\|` |
| 30 | `&&` |
| 40 | `==`, `!=` |
| 50 | `<`, `<=`, `>`, `>=` |
| 55 | `\|` |
| 57 | `&` |
| 58 | `<<`, `>>` |
| 60 | `+`, `-` |
| 70 | `*`, `/`, `%` |
| 80 | unary `-`, `!`, `~` |
| 90 | `^` (right-associative) |

### Other Expressions

All other expressions (ranges, identifiers, etc.) are rendered on a single line.

---

## 6. Parameter Formatting

These rules apply to parameter lists in both `function` and `module` declarations.

- Parameters are comma-separated with a single space after each comma.
- A default value is written directly after the parameter name with `=` and **no surrounding spaces**: `param=default`.
- A parameter whose default is `undef` is printed without any default — `undef` is the implicit default and showing it adds no information.

```
// source:  function foo(a=undef, b=3, c=undef) = ...
// printed: function foo(a, b=3, c) = ...
```

### Multiline parameter lists

When the full declaration header exceeds 100 characters, each parameter is placed on its own line, indented one level. The closing `)` returns to the original indent on its own line, followed by ` =` (functions) or ` {` (modules).

```
function long_name(
    param_a,
    param_b=10,
    param_c
) =
    expression;

module long_name(
    param_a,
    param_b=10,
    param_c
) {
    body;
}
```

The 100-character limit is measured against the full inline header: `function name(params) =` for functions and `module name(params)` for modules, including any leading indentation.

---

## 7. Function Declarations

```
function name(param1, param2=default) =
    expression;
```

- Parameter formatting follows [§6](#6-parameter-formatting).
- The header ends with ` =`; the body expression always starts on the next line, indented one level.
- Terminated with `;` on the last line of the expression.
- Ternary, assert, echo, and let bodies follow the multiline rules from [§5](#5-expressions).

```
function clamp(v, lo, hi) =
    v < lo
      ? lo
      : v > hi
        ? hi
        : v;
```

A blank line is inserted before and after each function declaration (see [§3](#3-blank-line-separation)).

---

## 8. Module Declarations

```
module name(param1, param2=default) {
    body;
}
```

- Parameter formatting follows [§6](#6-parameter-formatting).
- The body is always a braced block, never inline.
- Opening brace is on the same line as the header (or the closing `)` line when parameters are multiline), separated by one space.
- Closing brace is on its own line at the module's indentation level.
- An empty body is rendered as `{}` on the same line: `module m() {}`.

A blank line is inserted before and after each module declaration (see [§3](#3-blank-line-separation)).

---

## 9. Module Instantiations

### Leaf calls (no children)

```
cube(10);
sphere(r=5, $fn=32);
```

Terminated with `;`.

### Single child

A single child is placed on the next line, indented one level. No braces are used.

```
translate([1, 0, 0])
    cube(5);
```

### Multiple children

Multiple children are wrapped in a braced block. The opening brace follows the header on the same line, separated by one space.

```
union() {
    cube(5);
    sphere(3);
}
```

### Named arguments

Arguments are formatted as `name=value` (no spaces around `=` for named args) or just `value` for positional args. Multiple arguments are comma-space separated.

```
cube(size=10, center=true);
rotate([0, 0, 45])
    cube(5);
```

### Long argument lists

When the inline form of a module call (including its indentation) exceeds 100 characters, arguments are formatted one per line. The `(` stays on the header line, each argument is indented one level, and `)` returns to the original indent. Children then follow as normal.

```
some_module(
    very_long_argument_one,
    very_long_argument_two,
    very_long_argument_three,
    very_long_argument_four
) {
    cube(1);
    sphere(2);
}
```

### for and intersection_for

```
for (i = [0:10])
    cube(i);

for (i = [0:5]) {
    cube(i);
    sphere(i);
}

intersection_for (i = [0:3])
    cube(i);
```

The loop variable assignments use `=` with spaces. Multiple assignments are comma-space separated.

### let, echo, assert

These follow the same single-child / multi-child block rules as regular calls.

```
let (x = 1, y = 2)
    cube(x);

echo("value =", v);

assert(x > 0)
    cube(x);
```

`let` assignments follow the same inline/block rule as let expressions (see [§5](#5-expressions)): if any assignment value is multiline, `let` switches to the block format with one assignment per line:

```
let (
    dumwarn = some_condition || other_condition
      ? echo("deprecated warning")
      : 0
)
    cube(x);
```

---

## 10. Control Flow

### if (no else)

A single-child true branch is inline (next line, indented). A multi-child true branch uses a braced block.

```
if (condition)
    cube(1);

if (condition) {
    cube(1);
    sphere(2);
}
```

### if / else

The `else` connector placement depends on the shape of the true branch:

- **True branch is a block** (`{...}`): `else` is on the same line as the closing brace.
- **True branch is a single inline child**: `else` is on its own line at the same indentation.

```
// true branch is a block → else on same line
if (x > 0) {
    cube(1);
    sphere(2);
} else
    cylinder(3);

// true branch is single child → else on new line
if (x > 0)
    cube(1);
else
    sphere(2);
```

The false branch follows the same single/multi-child rules independently.

---

## 11. Modifiers

The four OpenSCAD debug modifiers (`!`, `#`, `%`, `*`) are prepended directly to the call with no space. Multiple nested modifiers are concatenated in order.

```
!cube(1);
#sphere(2);
%translate([0,0,0]) cube(1);
*cylinder(5);
!#cube(1);
```

---

## 12. Comments

Comments are only included in output when `include_comments=True` is passed to `getASTfromString()` (or equivalent). They are formatted as follows:

- **Line comments**: `// text` — the text is reproduced exactly as captured, including any leading space.
- **Block comments**: `/* text */` — the text is reproduced exactly as captured.

Comments appear at their own indentation level like any other statement.

---

## 13. Use and Include Statements

```
use <path/to/library.scad>
include <path/to/file.scad>
```

No semicolons. Angle brackets are preserved. No blank lines are inserted around these statements.
