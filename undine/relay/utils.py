from __future__ import annotations

import base64

__all__ = [
    "decode_base64",
    "encode_base64",
]


def encode_base64(string: str) -> str:
    return base64.b64encode(string.encode("utf-8")).decode("ascii")


def decode_base64(string: str) -> str:
    return base64.b64decode(string.encode("ascii")).decode("utf-8")
