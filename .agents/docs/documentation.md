# Documentation style

Docs live under `docs/`. Write in idiomatic English with simple language, second-person tone,
and concise paragraphs (1–3 sentences). Use simple punctuation, no em dashes or semicolons.
Read a few docs pages for reference before writing a new one.

## Content guidelines

- Order sections in teaching order (foundation first, then what the user applies), not alphabetical or spec order.
- Show, don't narrate: a code snippet plus a rendered output block teaches more than prose.
- Prefer subsections over Markdown tables.
- Give each first-class API entity its own subsection named after it.
- Cut design-decision justification and internal implementation detail.
- Don't preemptively enumerate errors or edge cases the user will hit once and understand from the error message.

## Page structure

Every page starts with a `description:` line, a blank line, then the `# Title`:

```markdown
description: Documentation on queries in Undine.

# Queries
```

- Open the body with a short paragraph stating what the page covers, linking to related pages inline.
- Use `##` for top-level topics, `###` for subsections, `####` only when necessary.
- Wrap every mention of a code entity (class, method, field, module, path) in backticks, including repeat mentions.
- Bold a new concept the first time it's introduced. Use backticks (not italics) for anything code-shaped.
- Follow the pattern: brief prose → code snippet → resulting output.

## Code examples

Python code examples must be added with snippets:

```python
-8 < -"page/example.py"
```

- Snippet directory mirrors the page name with underscores: `docs/file-upload.md` → `docs/snippets/file_uploads/`.
- Snippet file naming: `<entity>_<feature>.py`, e.g. `field_alias.py`, `filterset_decorator.py`.
- One snippet per concept. Don't bundle multiple concepts into a single snippet file.
- When a Python definition produces schema, always show the generated `graphql` block below it.
- Use fenced blocks with an explicit language: `python`, `graphql`, `json`, `pycon` (REPL with `>>>`), `shell`.
- Use `hl_lines="..."` on the fence (not the snippet directive) to point at the key lines.
- GraphQL examples should be added inline.

## Notes and collapsibles

- Use `> ` blockquotes for short inline notes, warnings, and "experimental feature" callouts. Never use `!!! note` admonitions.
- Use `/// details | Title` ... `///` blocks for collapsible content: expected responses, side discussions, per-entry reference sections.

Setting entries in `docs/settings.md` use this exact shape:

```markdown
/// details | `SETTING_NAME`
    attrs: {id: setting_name}

Type: `bool` | Default: `False`

Description of the setting.

///
```

## Links

Internal links use markdown file links:

```markdown
[SETTING_NAME](settings.md#setting_name)
```

External links open in a new tab and put the actual URL on a new line right after the paragraph, not at the end of the file or section.

```markdown
This is a [link]{:target="_blank"}

[link]: https://example.com/
```
