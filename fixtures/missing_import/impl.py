def average(nums: list[float]) -> float:
    """Return the arithmetic mean. Empty list -> 0.0."""
    if not nums:
        return 0.0
    # mean is used but never imported from statistics
    return mean(nums)
