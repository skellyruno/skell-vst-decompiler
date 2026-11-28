import random
import unittest
from skell_vst_decompiler.interval_index import IntervalIndex


class IntervalIndexTest(unittest.TestCase):
    def test_boundaries_and_nested_ranges(self):
        rows = {('a', 'outer'): (0, 100), ('a', 'inner'): (10, 20),
                ('a', 'adjacent'): (20, 30), ('b', 'other'): (10, 20)}
        index = IntervalIndex(rows)
        self.assertEqual(index.overlaps('a', 10, 20), {'outer', 'inner'})
        self.assertEqual(index.overlaps('a', 20, 30), {'outer', 'adjacent'})
        self.assertEqual(index.overlaps('a', 99, 100), {'outer'})
        self.assertEqual(index.overlaps('a', 100, 101), set())
        self.assertEqual(index.overlaps('missing', 10, 20), set())

    def test_randomized_against_linear_oracle(self):
        rng = random.Random(420)
        rows = {}
        for i in range(2500):
            lo = rng.randrange(10000)
            rows[(str(i % 4), str(i))] = (lo, lo + rng.randrange(1, 500))
        index = IntervalIndex(rows)
        for _ in range(1000):
            sha = str(rng.randrange(5))
            lo = rng.randrange(10000)
            hi = lo + rng.randrange(1, 250)
            expected = {name for (source, name), (start, end) in rows.items()
                        if source == sha and start < hi and lo < end}
            self.assertEqual(index.overlaps(sha, lo, hi), expected)

    def test_invalid_ranges(self):
        with self.assertRaises(ValueError):
            IntervalIndex({('a', 'bad'): (3, 2)})
        index = IntervalIndex({})
        with self.assertRaises(ValueError):
            index.overlaps('a', 0, 0)


if __name__ == '__main__':
    unittest.main()
