# Code style

- Never add module docstrings. Only add docstrings to classes, functions, or variables when necessary.
- Prefer unabbreviated names for classes, functions, and variables.
- Make all function arguments keyword-only when there are more than 3 of them
  (excluding `self` in methods), or when any two arguments share the same type.
- Prefer not returning tuples. Either split into separate functions called by the parent,
  or return a structured object like a `dataclass` or `TypedDict`.
- Use functions designed for the format instead of hand-rolling strings.
  For example, use `urllib.parse.urlencode` to build query strings.
- Assign class instances and function return values to variables before passing them
  as arguments or using them in comparisons.
