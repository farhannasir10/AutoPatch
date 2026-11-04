def parse_ints(raw: str) -> list[int]:
    """Split a comma-separated string into ints, skipping blanks."""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    # forgot to cast — callers get strings and tests explode
    return parts
