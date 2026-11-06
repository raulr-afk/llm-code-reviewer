def longest_unique_substring(s):
    # brute force: check every substring
    best = 0
    for i in range(len(s)):
        for j in range(i, len(s)):
            sub = s[i:j + 1]
            if len(set(sub)) == len(sub):
                best = max(best, len(sub))
    return best
