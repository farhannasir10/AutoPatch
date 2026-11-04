from impl import fizzbuzz


def test_fifteen():
    result = fizzbuzz(15)
    assert result[2] == "Fizz"
    assert result[4] == "Buzz"
    assert result[14] == "FizzBuzz"


def test_length():
    assert len(fizzbuzz(10)) == 10
