# Code style

## General

- Use functions designed for formatting strings instead of hand-rolling them, e.g. `urllib.parse.urlencode` to build query strings.
- Accept what the formatter and linter want. If a formatter rewrites imports or other code, keep the rewrite. Do not revert an autofix for any reason.
- Never use inline imports unless absolutely necessary. Don't assume it's needed before hitting an actual error.

## Readability

- Use unabbreviated names for classes, functions, and variables.
- Assign class instances and function return values to variables before passing them as arguments or using them in comparisons.
- Split long method chains (4+ steps) into multiple lines with intermediate variables or create a helper function.
- Split long comprehensions into multiple lines. Use generator expressions for intermediate results.

## Code comments

- Never comment what the code clearly says. If a reader gets it from the code in a few seconds, delete the comment.
- Only add one when the code is complex or surprising without context. Say why, not what.
- State a thing once. Two copies of one note drift apart, and then one of them is a lie.
- A comment that implies something the code no longer does is worse than no comment at all.
- Inline comments, block comments, standard docstrings, and attribute docstrings all count as comments.
- Exception: Docstrings in the public interface of the library, where they are used to teach the user how to use the library.
- Never add module docstrings, even in the public interface.

## Appropriate Coupling

Pick the loosest coupling that fits the relationship. Looser than the relationship needs adds an
abstraction that carries no meaning. Tighter spreads one change across many files.

Coupling has two axes. Mechanism is how the parts touch. Reason is why a change in one
reaches the other. Name both before changing shared code.

### Mechanism, strongest first

- Content: one part reads or writes another's internals. Private attributes, `_`-prefixed names, monkey-patching, reaching through an object into its members.
- Common: parts share mutable global state. Module-level dicts, singletons, thread locals.
- External: parts share a format, protocol, or schema imposed from outside. Neither side owns the change.
- Control: a caller passes a flag that picks the callee's branch, so the caller holds the callee's structure.
- Stamp: a caller passes a whole object where the callee uses two fields, so the callee holds the whole shape.
- Data: the callee takes exactly the values it uses. This is the target.

### Reason

- Functional: the parts implement pieces of one behavior, so a change to that behavior lands in both.
- Semantic: the parts share one domain concept, so a change in what the concept means lands in both.
- Development: a change to one part forces an edit to the other. This is the cost while writing code.
- Operational: one part cannot run without the other. This is the cost at runtime.
- Incidental: the parts share no behavior and no concept. The link is an accident of how the code grew. Delete it rather than manage it.

### Chains

Coupling composes. A view stamp-coupled to a serializer that is semantically coupled to a model
means a change in the model's meaning reaches the view. Follow the chain before changing a shared
type. What must change is the whole chain, not the direct caller.

Distance sets the price. A strong link inside one module is cheap, because the whole chain is in
front of you. The same link across a package boundary carries the change further at every step.

### Choosing strength

Judge by volatility: how often the interface has changed, and how often it is expected to change.

- Stable interface: couple directly and strongly. An abstraction here is one more layer to read through.
- Volatile interface: put an abstraction between the parts, so the change stops at the abstraction instead of reaching every caller.

Practicality beats purity. A strong coupling that is easy to read and easy to find beats an
indirection that hides where the behavior lives.

## Function structure

- Make all function arguments keyword-only when there are more than 3 of them (excluding self in methods), or when any two arguments share the same type.
- Do not return tuples. Either split into separate functions called by the parent, or return a structured object like a dataclass, NamedTuple or TypedDict.

## Class structure

- Prefer functions over classes.
- Prefer dataclasses over plain classes.
- Use composition and dependency injection instead of inheritance and mixins.

## Module structure

- Inside a module, put the module interface (public names) at the top and the internal implementation (non-public names) at the bottom.
- Prefer deep modules: small interface, deep implementation. A few methods with simple params hiding complex logic behind them.
- Avoid shallow modules: large interface with many methods that just pass through to thin implementation. When designing, ask: can I reduce the number of methods? Can I simplify the parameters? Can I hide more complexity inside?

## Error handling

- Never raise built-in or third-party exceptions manually. Always create a custom exception instead.
- Never put a caught built-in or third-party exception's message into a custom exception or HTTP response that reaches the client. It may expose internal implementation details. Log the full exception server-side then raise or return a fixed, safe message instead.
- Use the shared `logger` from `undine/utils/logging.py` instead of creating a per-module logger.
