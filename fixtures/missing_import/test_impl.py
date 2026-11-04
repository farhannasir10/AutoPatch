from impl import average


def test_average_basic():
    assert average([2, 4, 6]) == 4.0


def test_average_empty():
    assert average([]) == 0.0


def test_average_floats():
    assert average([1.5, 2.5]) == 2.0
