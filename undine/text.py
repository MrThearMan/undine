import re

__all__ = [
    "to_camel_case",
]


ALLOWED_NAME = re.compile(r"^[a-z][_0-9a-z]*$")


def check_snake_case(string: str) -> str:
    """Check if a string is in snake case. All words also need to be in lower case."""
    if re.match(ALLOWED_NAME, string) is None:
        msg = f"'{string}' is not a valid snake case."
        raise ValueError(msg)
    return string


def to_camel_case(snake_case_str: str) -> str:
    """Convert a snake case string to camel case. Input is validated to be in snake case."""
    words = iter(check_snake_case(snake_case_str).split("_"))
    text = next(words)
    for word in words:
        text += word.capitalize()
    return text
