import re

__all__ = [
    "camel_case_to_name",
    "name_to_camel_case",
    "name_to_pascal_case",
]


# fmt: off
ALLOWED_NAME = re.compile(
    r"^"          # Start of string
    r"[a-z]"      # First character must be a letter.
    r"(?:"        # Followed by (non-capturing group):
    r"[a-z0-9]"   # 1) Any number of letters or numbers
    r"|"          # OR
    r"(_[a-z])"   # 2) An underscore followed by a letter
    r")*"         # Zero or more of the above
    r"$"          # End of string
)
# fmt: on


def validate_name(name: str) -> str:
    """
    Check whether the name is valid.
    Valid names can be converted to 'camelCase' and back to 'snake_case' unambigously.
    """
    if re.match(ALLOWED_NAME, name) is None:
        msg = (
            f"'{name}' is not not an allowed name. "
            f"Names must be in 'snake_case', all lower case, and cannot begin or end with an underscore. "
            f"Also, any underscores must be followed by a letter due ambiguousness when converting "
            f"values like 'the_1st' vs 'the1st' to 'camelCase' and then back to 'snake_case'."
        )
        raise ValueError(msg)
    return name


def name_to_camel_case(name: str) -> str:
    """
    Convert a name to camelCase.
    Validates that name can be converted back to snake case unambigously.
    """
    words = iter(validate_name(name).split("_"))
    text = next(words)
    for word in words:
        text += word.capitalize()
    return text


def name_to_pascal_case(name: str) -> str:
    """
    Convert a name to PascalCase.
    Validates that name can be converted back to snake case unambigously.
    """
    words = iter(validate_name(name).split("_"))
    text = ""
    for word in words:
        text += word.capitalize()
    return text


def camel_case_to_name(string: str) -> str:
    """
    Converts a camelCase string to snake case.
    It's expected that the input string was created by 'name_to_camel_case'.
    """
    text: str = ""
    for char in string:
        if char.isupper():
            text += "_"
        text += char.lower()
    return text
