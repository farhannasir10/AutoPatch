from impl import is_palindrome


def test_simple_palindrome():
    assert is_palindrome("racecar") is True


def test_mixed_case():
    assert is_palindrome("RaceCar") is True


def test_with_spaces():
    assert is_palindrome("A man a plan a canal Panama") is True


def test_not_palindrome():
    assert is_palindrome("hello") is False
