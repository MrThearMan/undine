from undine.relay import cursor_to_offset, decode_base64, encode_base64, from_global_id, offset_to_cursor, to_global_id


def test_encode_base64():
    assert encode_base64("foo") == "Zm9v"


def test_decode_base64():
    assert decode_base64("Zm9v") == "foo"


def test_offset_to_cursor():
    assert offset_to_cursor("Test", 1) == "Y29ubmVjdGlvbjpUZXN0OjE="


def test_cursor_to_offset():
    assert cursor_to_offset("Test", "Y29ubmVjdGlvbjpUZXN0OjE=") == 1


def test_to_global_id():
    assert to_global_id("TaskType", 1) == "SUQ6VGFza1R5cGU6MQ=="


def test_from_global_id():
    assert from_global_id("SUQ6VGFza1R5cGU6MQ==") == ("TaskType", 1)
