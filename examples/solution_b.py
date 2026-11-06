def longest_unique_substring(s: str) -> int:
    """Sliding window with a dict of last-seen indices. O(n) time."""
    last_seen = {}
    start = 0
    best = 0
    for index, char in enumerate(s):
        if char in last_seen and last_seen[char] >= start:
            start = last_seen[char] + 1
        last_seen[char] = index
        best = max(best, index - start + 1)
    return best
