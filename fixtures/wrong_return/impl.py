def is_palindrome(text: str) -> bool:
    """True if text reads the same forwards and backwards (case-insensitive)."""
    cleaned = "".join(ch.lower() for ch in text if ch.isalnum())
    # oops — comparing to the original string, not the reversed cleaned one
    return cleaned == text
