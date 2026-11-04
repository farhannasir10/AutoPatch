def fizzbuzz(n: int) -> list[str]:
    """Classic fizzbuzz for 1..n inclusive."""
    out: list[str] = []
    for i in range(1, n + 1):
        # conditions are swapped — multiples of 15 never hit "FizzBuzz"
        if i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        elif i % 15 == 0:
            out.append("FizzBuzz")
        else:
            out.append(str(i))
    return out
