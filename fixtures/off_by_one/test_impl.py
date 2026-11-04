from impl import sum_to_n


def test_sum_to_n_small():
    assert sum_to_n(5) == 15


def test_sum_to_n_one():
    assert sum_to_n(1) == 1


def test_sum_to_n_zero():
    assert sum_to_n(0) == 0
