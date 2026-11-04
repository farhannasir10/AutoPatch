from impl import parse_ints


def test_basic():
    assert parse_ints("1, 2, 3") == [1, 2, 3]


def test_with_blanks():
    assert parse_ints("10,,20,") == [10, 20]


def test_empty():
    assert parse_ints("") == []
