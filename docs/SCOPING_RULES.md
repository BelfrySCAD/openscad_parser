# OpenSCAD Scoping Rules

This document provides a comprehensive reference for OpenSCAD's variable scoping rules. It covers both lexical scoping for regular variables and dynamic scoping for `$`-prefixed special variables. This serves as the specification for implementing scope-aware AST traversal.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Lexical Scoping (Regular Variables)](#2-lexical-scoping-regular-variables)
3. [Dynamic Scoping ($-prefixed Variables)](#3-dynamic-scoping--prefixed-variables)
4. [Namespaces and Resolution Rules](#4-namespaces-and-resolution-rules)
5. [Use vs Include Behavior](#5-use-vs-include-behavior)
6. [Edge Cases and Special Behaviors](#6-edge-cases-and-special-behaviors)
7. [Examples](#7-examples)
8. [AST Node Reference Table](#8-ast-node-reference-table)

---

## 1. Introduction

OpenSCAD uses a **dual scoping model**:

- **Lexical scoping** for regular variables (e.g., `x`, `width`, `my_value`)
- **Dynamic scoping** for special variables prefixed with `$` (e.g., `$fn`, `$fa`, `$fs`)

This combination is unusual among programming languages and requires careful understanding to use effectively.

### Key Differences from C-like Languages

- **Limited block scoping**: Bare braces `{ }` do NOT create new scopes, but `if/else` branches DO
- **Single-assignment semantics**: Variables cannot be reassigned within a scope (but can be shadowed)
- **Hoisted evaluation**: All assignments in a scope are evaluated before any module instantiations
- **Three separate namespaces**: Functions, modules, and variables can share the same name
- **Lexical closure**: Modules and functions inherit the lexical scope where they were *declared*, not where they are *called*

---

## 2. Lexical Scoping (Regular Variables)

### 2.1 Single-Assignment Semantics

Within a single scope level, a variable name can only be assigned once. However, inner scopes can **shadow** variables from outer scopes by using the same name.

```openscad
x = 10;
// x = 20;  // ERROR: Cannot reassign x in the same scope

module foo() {
    x = 20;  // OK: This shadows the outer x
    echo(x); // Outputs: 20
}
```

### 2.2 What Does NOT Create a Scope

Unlike C/C++ and many other languages, the following constructs do **NOT** create new variable scopes:

#### Bare Braces `{ }`

Braces are merely statement grouping, not scope boundaries:

```openscad
{
    y = 42;
}
echo(y);  // Works! Outputs: 42 - y "leaks" out of the braces
```

#### Module Calls

When you call a module, the module executes in its own scope, but the **call site** does not create a new scope:

```openscad
cube(10);  // No new scope created at this line
x = 5;     // x is in the same scope as the cube() call
```

### 2.3 Scope-Creating Constructs

The following constructs **DO** create new variable scopes:

| Construct | AST Node | Scope Contains |
|-----------|----------|----------------|
| Module declaration | `ModuleDeclaration` | Parameters + body (including nested function/module declarations) |
| Function declaration | `FunctionDeclaration` | Parameters + expression |
| Expression-level let | `LetOp` | Assignments + trailing expression |
| Statement-level let | `ModularLet` | Assignments + children |
| If statement | `ModularIf` | True branch only |
| If-else statement | `ModularIfElse` | Each branch creates separate scope |
| For loop (statement) | `ModularFor` | Loop variables + body |
| C-style for (statement) | `ModularCFor` | Loop variables + body |
| Intersection for | `ModularIntersectionFor` | Loop variables + body |
| C-style intersection for | `ModularIntersectionCFor` | Loop variables + body |
| Module instantiation children | `ModularCall` (children) | Children of a module call |
| For loop (list comprehensions) | `ListCompFor` | Loop variables + body |
| C-style for (list comprehensions) | `ListCompCFor` | Loop variables + body |
| Let (list comprehensions) | `ListCompLet` | Assignments + body |
| Anonymous function | `FunctionLiteral` | Parameters + body |

**Note:** `ListCompIf` and `ListCompIfElse` do **NOT** create new scopes - they are expression-level conditional filters within list comprehensions, not modular scope boundaries.

#### Module Declaration

When a module is instantiated, it can see:

1. **Parameters** defined in the module declaration
2. **Lexical scope from where it was declared** (not where it's called)
3. **$variables** inherited dynamically from the caller

**Nested Declarations**: Modules and functions can be declared inside a module body. These are scoped to the containing module and not visible outside:

```openscad
module outer() {
    function helper(x) = x * 2;  // Only visible inside outer()
    module inner() { cube(1); }  // Only visible inside outer()

    inner();           // OK
    echo(helper(5));   // OK
}

// helper() and inner() are NOT visible here
inner();               // ERROR: inner is not defined
```

```openscad
decl_scope_var = 100;

module foo() {
    echo(decl_scope_var);   // Sees 100 from declaration scope
}

module bar() {
    decl_scope_var = 999;   // Local to bar
    foo();                  // foo still sees 100, not 999!
}

bar();  // Outputs: 100
```

The key distinction: regular variables come from **declaration scope**, `$variables` come from **call scope**:

```openscad
x = 10;
$y = 10;

module inner() {
    echo("x =", x);         // From declaration scope
    echo("$y =", $y);       // From call scope (dynamic)
}

module outer() {
    x = 20;                 // Local x (shadows, but inner doesn't see it)
    $y = 20;                // $y inherited by children
    inner();
}

outer();
// Outputs:
//   x = 10   (lexical - from where inner was declared)
//   $y = 20  (dynamic - from where inner was called)
```

#### Function Declaration

Functions see their parameters plus variables from the complete scope **where they were declared**:

```openscad
scale_factor = 2;

function scaled_area(w, h) = w * h * scale_factor * aspect;

aspect = 1.5;

// w and h are parameters
// scale_factor and aspect are from declaration scope

echo(scaled_area(3, 4));  // Outputs: 36

module test() {
    scale_factor = 100;           // Local to test
    echo(scaled_area(3, 4));      // Still outputs 36! Uses scale_factor=2
}
```

#### Expression-Level Let (`LetOp`)

```openscad
x = let(foo=3, bar=4) foo * bar;
// foo and bar are ONLY in scope for the expression "foo * bar"
// x gets the value 12
echo(foo);  // ERROR: foo is not defined here
```

#### Statement-Level Let (`ModularLet`)

```openscad
let(foo=3, bar=4)
    square([foo, bar]);
// foo and bar are in scope for the children of let()
```

#### If/Else Statements (`ModularIf`, `ModularIfElse`)

Variables assigned inside if/else branches are only visible within that branch:

```openscad
if (condition) {
    x = 10;
    cube(x);      // OK: x is in scope
}
echo(x);          // ERROR: x is not defined here
```

Each branch creates its own scope:

```openscad
if (flag) {
    val = 100;
} else {
    val = 200;
}
echo(val);        // ERROR: val is not defined here
```

#### For Loops

```openscad
for (i = [0:10]) {
    // i is in scope here
    cube(i);
}
// i is NOT in scope here
```

### 2.4 Shadowing Rules

Inner scopes can shadow variables from outer scopes:

```openscad
x = 10;

module test() {
    x = 20;      // Shadows outer x
    echo(x);     // Outputs: 20
}

test();
echo(x);         // Outputs: 10 (outer x unchanged)
```

Shadowing also works with parameters:

```openscad
x = 10;

module test(x) {   // Parameter x shadows global x
    echo(x);
}

test(99);          // Outputs: 99
```

### 2.5 Assignment Scoping Rule

A variable declared by an assignment statement does **not** come into scope until **after** the assignment statement. The right-hand side expression cannot reference the variable being defined:

```openscad
x = x + 1;  // ERROR: x is not defined in the RHS expression
y = 10;
z = y + 1;  // OK: y is already defined
```

**Exception - Function Literals**: The body of a function literal inherits the complete scope of where is is declared. This enables recursion:

```openscad
fn = function(a) a<2? 1 : a * fn(a-1) + b;  // fn and b are both in scope inside the function literal
b = 3;
```

### 2.6 Evaluation Order Within a Scope Level (Hoisting)

**Critical rule**: Within any **modular sub-block**, all declarations (assignments, function declarations, module declarations) are collected **BEFORE** any module instantiations are evaluated.

Modular sub-blocks include:
- Top-level file scope
- Module declaration bodies
- Each branch of `ModularIf` / `ModularIfElse`
- Body of `ModularFor` / `ModularCFor` / `ModularIntersectionFor` / `ModularIntersectionCFor`
- Children of `ModularCall` (module instantiation children)
- Children of `ModularLet` / `ModularEcho` / `ModularAssert`

This means assignments are effectively "hoisted" - a variable assigned later in the block is visible to module calls that appear earlier in the source code:

```openscad
module test() {
    cube(x);     // Uses x = 20, not undefined!
    x = 10;
    sphere(x);   // Uses x = 20
    x = 20;      // This is the final value of x
}
```

**Evaluation sequence:**
1. `x = 10` is evaluated
2. `x = 20` is evaluated (x is now 20)
3. `cube(x)` is instantiated with x = 20
4. `sphere(x)` is instantiated with x = 20

**Key distinction**: Hoisting applies to module instantiations seeing variables, but the RHS of an assignment still cannot see the variable being defined (see Section 2.5).

### 2.7 Multiple Assignments at Same Scope Level

When the same variable is assigned multiple times at the same scope level, the **last assignment wins**:

```openscad
x = 1;
x = 2;
x = 3;
echo(x);  // Outputs: 3
```

This combines with the hoisting rule to create potentially surprising behavior (see Section 2.6).

### 2.8 Default Parameter Evaluation

Default parameter values are evaluated in the scope of the place where the function, module, or function literal are declared:

```openscad
y = 100;

module test(x = y) {
    y = 50;      // This does NOT affect the default
    echo(x);
}

test();          // Outputs: 100
if (true) {
    y = 25;
    test();      // Still outputs 100.
}
```

---

## 3. Dynamic Scoping ($-prefixed Variables)

Variables prefixed with `$` use **dynamic scoping**, which means their values are inherited through the call chain at runtime, not determined by lexical (textual) location.

### 3.1 How $variables Differ from Regular Variables

| Aspect | Regular Variables | $variables |
|--------|-------------------|------------|
| Scoping | Lexical (textual) | Dynamic (runtime call chain) |
| Inherited from | Scope where function/module was **declared** | Scope where function/module was **called** |
| Use case | Local computation | Configuration, context passing |

### 3.2 Inheritance Through Module Calls

When a module is called, it inherits all `$variables` from its caller:

```openscad
$my_setting = 10;

module parent() {
    $my_setting = 20;
    child();         // child sees $my_setting = 20
}

module child() {
    echo($my_setting);
}

parent();            // Outputs: 20
child();             // Outputs: 10 (called from top level)
```

### 3.3 Children Inherit Parent's $variable Scope

When a module is called with children, the children see the `$variables` as modified inside the parent module.

**Syntax note:** Braces are only required for multiple children. A single child can be passed without braces:

```openscad
parent() child();                    // Single child - no braces needed
parent() { child1(); child2(); }     // Multiple children - braces required
```

Example of $variable inheritance:

```openscad
$size = 5;

module enlarge() {
    $size = $size * 2;
    children();
}

enlarge() {
    cube($size);     // Uses $size = 10, not 5!
}
```

This is **dynamic scoping** - the child sees the `$variable` values from where it's *called*, not where it's *defined*.

### 3.4 Common Built-in $variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `$fn` | Number of fragments for circles/spheres | 0 (auto) |
| `$fa` | Minimum angle in degrees for fragments | 12 |
| `$fs` | Minimum size/length for fragments | 2 |
| `$t` | Animation time (0.0 to 1.0) | 0.0 |
| `$children` | Number of child modules | 0 |
| `$preview` | True if in preview mode | - |
| `$parent_modules` | Stack of parent module names | - |

### 3.5 User-Defined $variables

You can define your own `$variables` for passing configuration down the call chain:

```openscad
$wall_thickness = 2;
$tolerance = 0.2;

module box() {
    // Uses $wall_thickness and $tolerance from caller
    difference() {
        cube([10, 10, 10]);
        translate([$wall_thickness, $wall_thickness, $wall_thickness])
            cube([10 - 2*$wall_thickness,
                  10 - 2*$wall_thickness,
                  10 - $wall_thickness + $tolerance]);
    }
}
```

### 3.6 Passing $variables as Module Arguments

You can pass `$variables` as arguments when instantiating modules. These `$variables` are then available to the children of that module:

```openscad
module foo() {
    children();
}

foo($fee=7) {
    square($fee);    // Uses $fee = 7
}
```

This allows you to pass `$variables` directly at the call site, making them available to the module's children without needing to assign them in the module body:

```openscad
module container() {
    children();
}

container($width=10, $height=5) {
    cube([$width, $height, 2]);  // Uses $width=10, $height=5
}
```

A `$variable` passed as an argument will **shadow** any previous value of that `$variable` from the caller's scope:

```openscad
$size = 5;

module wrapper() {
    children();
}

wrapper($size=20) {
    cube($size);    // Uses $size = 20, not 5 (argument shadows caller's value)
}
```

### 3.7 Recent Changes (Needs Research)

> **Note:** There have been recent controversial changes to `$variable` scoping behavior at the top-level context. These changes were discussed on the OpenSCAD mailing list. The exact details need to be researched and documented here.

---

## 4. Namespaces and Resolution Rules

### 4.1 Three Independent Namespaces

OpenSCAD maintains **three separate namespaces**:

1. **Functions namespace** - for function declarations
2. **Modules namespace** - for module declarations
3. **Variables namespace** - for variable assignments

The same identifier can exist in all three namespaces simultaneously:

```openscad
foobar = 10;                    // Variable named foobar

function foobar() = 20;         // Function named foobar

module foobar() {               // Module named foobar
    cube(30);
}

echo(foobar);                   // Outputs: 10 (the variable)
echo(foobar());                 // Outputs: 20 (the function)
foobar();                       // Instantiates the module (cube)
```

### 4.2 Function Call Resolution in Expression Context

When a call like `qux()` appears in an expression context (e.g., right side of assignment):

1. **First**, check for a variable named `qux` in the local scope that might contain a function literal
2. **If not found**, look for a function named `qux` in the function namespace

```openscad
function qux() = 10;

x = qux();                      // Calls the function, x = 10

qux = function() 20;            // Variable holding function literal
y = qux();                      // Calls the variable's function, y = 20
```

### 4.3 Function vs Module Determination

Whether a name resolves to a function or module depends on **context**:

| Context | Resolution |
|---------|------------|
| Expression (e.g., assignment RHS) | Function |
| Statement/Instantiation | Module |

```openscad
function cube(x) = x * x * x;   // Function named cube
// module cube is built-in      // Module named cube

volume = cube(3);               // Calls FUNCTION, volume = 27
cube(3);                        // Instantiates MODULE (3D cube)
```

### 4.4 Variable Lookup Algorithm

For regular variables, lookup proceeds from innermost to outermost scope:

1. Check current scope (function body, module body, let bindings, etc.)
2. Check enclosing scopes, moving outward
3. Check global/file scope
4. If not found, a WARNING is issued that the variable is undefined

### 4.5 Handling Undefined Variables

Referencing an undefined variable throws a WARNING that the variable is undefined:

```openscad
echo(nonexistent);              // WARNING: Variable "nonexistent" is not defined
x = nonexistent + 1;            // WARNING: Variable "nonexistent" is not defined
echo(x);                        // Outputs undef
```

---

## 5. Use vs Include Behavior

### 5.1 `use <file>`

The `use` statement imports **functions and modules** from another file, but **NOT variables**:

```openscad
// library.scad
lib_var = 100;
function lib_func() = 42;
module lib_mod() { cube(10); }

// main.scad
use <library.scad>

echo(lib_var);                  // ERROR: lib_var not accessible
echo(lib_func());               // OK: Outputs 42
lib_mod();                      // OK: Creates cube
```

### 5.2 `include <file>`

The `include` statement effectively **inserts the file contents** at that point, making all functions, modules, AND variables available:

```openscad
// library.scad
lib_var = 100;
function lib_func() = 42;
module lib_mod() { cube(10); }

// main.scad
include <library.scad>

echo(lib_var);                  // OK: Outputs 100
echo(lib_func());               // OK: Outputs 42
lib_mod();                      // OK: Creates cube
```

### 5.3 Summary

| Statement | Functions | Modules | Variables |
|-----------|-----------|---------|-----------|
| `use <file>` | Imported | Imported | NOT imported |
| `include <file>` | Imported | Imported | Imported |

---

## 6. Edge Cases and Special Behaviors

### 6.1 Braces Don't Create Scopes

Variables assigned inside braces are visible outside:

```openscad
{
    inner = 42;
}
echo(inner);                    // Outputs: 42
```

### 6.2 Variables in If/Else Branches

Variables assigned in if/else branches are scoped to that branch only:

```openscad
if (true) {
    branch_var = 20;
    echo(branch_var);           // Outputs: 20
}
echo(branch_var);               // ERROR: branch_var not defined here
```

This is different from bare braces, which do NOT create a scope.

### 6.3 Recursive Function/Module References

Functions and modules can reference themselves:

```openscad
function factorial(n) = n <= 1 ? 1 : n * factorial(n - 1);
echo(factorial(5));             // Outputs: 120
```

### 6.4 Forward References Within Same Scope Level

Due to hoisting, forward references work:

```openscad
echo(later_var);                // Outputs: 10 (due to hoisting)
later_var = 10;
```

### 6.5 Default Parameter Gotchas

Default parameters **cannot** reference earlier parameters. They are evaluated in the caller's scope:

```openscad
w = 100;
module box(w, h, d=w) {         // d=w refers to global w, not parameter w
    cube([w, h, d]);
}
box(10, 5);                     // Creates 10x5x100 cube (d uses global w=100, not parameter w=10)
```

Default parameter values are always evaluated in the caller's scope, not the function/module's parameter scope.

---

## 7. Examples

### 7.1 Shadowing Example

```openscad
x = "global";

module outer() {
    x = "outer";
    echo("In outer:", x);       // Outputs: outer

    module inner() {
        x = "inner";
        echo("In inner:", x);   // Outputs: inner
    }

    inner();
    echo("Back in outer:", x);  // Outputs: outer
}

outer();
echo("At global:", x);          // Outputs: global
```

### 7.2 $variable Inheritance Example

```openscad
$color = "red";

module paint() {
    $color = "blue";
    children();
}

module show_color() {
    echo($color);
}

show_color();                   // Outputs: red

paint() {
    show_color();               // Outputs: blue (inherited from paint)
}
```

### 7.3 Evaluation Order Example

```openscad
module demo() {
    echo("a =", a);             // Outputs: a = 3 (final value)
    a = 1;
    echo("b =", b);             // Outputs: b = 2 (final value)
    a = 2;
    b = 2;
    a = 3;
}
demo();
```

### 7.4 Namespace Example

```openscad
// All three coexist
thing = 10;
function thing() = 20;
module thing() { sphere(30); }

x = thing;                      // x = 10 (variable)
y = thing();                    // y = 20 (function)
thing();                        // Creates sphere (module)
```

---

## 8. AST Node Reference Table

Quick reference mapping AST nodes to their scope-related fields:

| AST Node | Bindings Field | Scope Body Field | Notes |
|----------|---------------|------------------|-------|
| `ModuleDeclaration` | `parameters` | `children` | Parameters + nested functions/modules |
| `FunctionDeclaration` | `parameters` | `expr` | Parameters are `ParameterDeclaration` |
| `LetOp` | `assignments` | `body` | Expression-level let |
| `ModularLet` | `assignments` | `children` | Statement-level let |
| `ModularIf` | - | `true_branch` | Branch creates scope |
| `ModularIfElse` | - | `true_branch`, `false_branch` | Each branch creates separate scope |
| `ModularFor` | `assignments` | `body` | Loop variables in `assignments` |
| `ModularCFor` | `initial`, `increment` | `body` | C-style for loop |
| `ModularIntersectionFor` | `assignments` | `body` | Intersection for loop |
| `ModularIntersectionCFor` | `initial`, `increment` | `body` | C-style intersection for |
| `ModularCall` | - | `children` | Module instantiation children create scope |
| `ListCompFor` | `assignments` | `body` | List comprehension for |
| `ListCompCFor` | `initial`, `increment` | `body` | List comprehension c-for |
| `ListCompLet` | `assignments` | `body` | List comprehension let |
| `FunctionLiteral` | `arguments` | `body` | Anonymous function |
| `Assignment` | `name` | - | Top-level variable binding |
| `ParameterDeclaration` | `name`, `default` | - | Used in function/module params |

**Note:** `ListCompIf` and `ListCompIfElse` do NOT create scopes - they are expression-level conditional filters.

### Field Details

- **`parameters`**: List of `ParameterDeclaration` nodes
- **`assignments`**: List of `Assignment` nodes
- **`children`**: List of `ModuleInstantiation` nodes
- **`body`**: Single expression or instantiation node
- **`initial`/`increment`**: Lists of `Assignment` nodes (C-style loops)
- **`name`**: `Identifier` node containing the variable name
- **`default`**: Optional `Expression` for default value
