"""Fingerprint-scoped interval lookups for existing evidence metadata."""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from itertools import accumulate


class IntervalIndex:
    def __init__(self, regions):
        groups = defaultdict(list)
        for (sha, name), (lo, hi) in regions.items():
            if not 0 <= lo < hi <= 2**32:
                raise ValueError('Invalid interval')
            groups[sha].append((lo, hi, name))
        self.groups = {}
        for sha, entries in groups.items():
            entries.sort()
            self.groups[sha] = (entries, [e[0] for e in entries],
                                list(accumulate((e[1] for e in entries), max)))

    def overlaps(self, sha, lo, hi):
        if not 0 <= lo < hi <= 2**32:
            raise ValueError('Invalid query interval')
        if sha not in self.groups:
            return set()
        entries, starts, max_ends = self.groups[sha]
        first = bisect_right(max_ends, lo)
        stop = bisect_left(starts, hi)
        return {entries[i][2] for i in range(first, stop) if entries[i][1] > lo}
