
from undine.relay import cursor_to_offset, decode_base64, encode_base64, from_global_id, offset_to_cursor, to_global_id


def test_encode_base64():
    assert encode_base64("foo") == "Zm9v"


def test_decode_base64():
    assert decode_base64("Zm9v") == "foo"


def test_offset_to_cursor():
    assert offset_to_cursor(1) == "YXJyYXljb25uZWN0aW9uOjE="


def test_cursor_to_offset():
    assert cursor_to_offset("YXJyYXljb25uZWN0aW9uOjE=") == 1


def test_to_global_id():
    assert to_global_id("TaskType", 1) == "VGFza1R5cGU6MQ=="


def test_from_global_id():
    assert from_global_id("VGFza1R5cGU6MQ==") == ("TaskType", 1)
