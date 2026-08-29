# Code style

## General

- Use functions designed for formatting strings instead of hand-rolling them, e.g. `urllib.parse.urlencode` to build query strings.
- Accept what the formatter and linter want. If a formatter rewrites imports or other code, keep the rewrite. Do not revert an autofix for any reason.
- Only add comments when the code is surprising without context. Never comment what the code clearly says.
- Never use inline imports unless absolutely necessary. Don't assume it's needed before hitting an actual error.

## Readability

- Use unabbreviated names for classes, functions, and variables.
- Assign class instances and function return values to variables before passing them as arguments or using them in comparisons.
- Split long method chains (4+ steps) into multiple lines with intermediate variables or create a helper function.
- Split long comprehensions into multiple lines. Use generator expressions for intermediate results.

## Function structure

- Make all function arguments keyword-only when there are more than 3 of them (excluding self in methods), or when any two arguments share the same type.
- Do not return tuples. Either split into separate functions called by the parent, or return a structured object like a dataclass, NamedTuple or TypedDict.
- Only add docstrings when you cannot infer something from the code (still keep it short and concise).

## Class structure

- Prefer functions over classes.
- Prefer dataclasses over plain classes.
- Use composition and dependency injection instead of inheritance and mixins.
- Only add docstrings when you cannot infer something from the code (still keep it short and concise).

## Module structure

- Never add module docstrings.
- Inside a module, put the module interface (public names) at the top and the internal implementation (non-public names) at the bottom.
- Prefer deep modules: small interface, deep implementation. A few methods with simple params hiding complex logic behind them.
- Avoid shallow modules: large interface with many methods that just pass through to thin implementation. When designing, ask: can I reduce the number of methods? Can I simplify the parameters? Can I hide more complexity inside?

## Error handling

- Never raise built-in or third-party exceptions manually. Always create a custom exception instead.
- Never put a caught built-in or third-party exception's message into a custom exception or HTTP response that reaches the client. It may expose internal implementation details. Log the full exception server-side then raise or return a fixed, safe message instead.
- Use the shared `logger` from `undine/utils/logging.py` instead of creating a per-module logger.
