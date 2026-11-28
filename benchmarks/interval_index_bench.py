"""Synthetic evidence interval benchmark, not a decompiler or audio benchmark."""
from skell_vst_decompiler.interval_index import IntervalIndex
from time import perf_counter
import random
import statistics
import json
import platform


def main():
    rng = random.Random(420)
    rows = {(str(i % 8), str(i)): (i*32, i*32+rng.randrange(1,256)) for i in range(40000)}
    queries = [(str(rng.randrange(8)), rng.randrange(1280000)) for _ in range(500)]
    linear, indexed, build = [], [], []
    for _ in range(3):
        t = perf_counter()
        a = [{name for (source,name),(start,end) in rows.items()
              if source == sha and start < lo+128 and lo < end} for sha,lo in queries]
        linear.append(perf_counter()-t)
        t = perf_counter()
        index = IntervalIndex(rows)
        build.append(perf_counter()-t)
        t = perf_counter()
        b = [index.overlaps(sha,lo,lo+128) for sha,lo in queries]
        indexed.append(perf_counter()-t)
        if a != b:
            raise AssertionError('Indexed results diverged')
    print(json.dumps({'regions':len(rows),'queries':len(queries),'repetitions':3,
                      'median_linear_seconds':statistics.median(linear),
                      'median_index_build_seconds':statistics.median(build),
                      'median_indexed_query_seconds':statistics.median(indexed),
                      'median_end_to_end_seconds':statistics.median([x+y for x,y in zip(build,indexed)]),
                      'python':platform.python_version(),'platform':platform.machine(),
                      'all_equal':True},indent=2))


if __name__ == '__main__':
    main()
