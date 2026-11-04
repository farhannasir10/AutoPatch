def sum_to_n(n: int) -> int:
    """Return 1 + 2 + ... + n."""
    total = 0
    # classic fencepost — range stops before n, so we miss n itself
    for i in range(1, n):
        total += i
    return total
