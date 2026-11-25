# Executable extent union coverage

Previous d82759a575cda0c4854f6d4138fd11026ab9c9bc: 168 regression tests and all eight CI workflows passed, including the Evo math-import and stacked-flanger tests. Reopened six exact original binary fingerprints and verified the atlas blob and VMR archive. New bounded read-only PE32/PE32+ metadata audit computes union and intersection byte coverage. No target loading or private inputs sent to CI.

The earlier 112/128 figure measured unique single-record containment. Full coverage by the union of adjacent records is a different metric: 117/128, with 2 partial and 9 no-coverage scopes. Five previously excluded regions (TVB three, FG-2A two) are fully covered by adjacent records. Every archived scope is within conservative mapped file-backed executable extents. No claim of additional runtime reachability. Across 128 scopes 47,570 summed bytes become 41,150 distinct bytes when overlap is removed; 40,029 are covered by runtime extents, 1,121 not. Per-binary deduplication only, no comparisons across differing fingerprints.

| Track | Distinct archived bytes | Runtime extent covered | Uncovered |
|---|---:|---:|---:|
| TVB | 20448 | 19983 | 465 |
| FG-116 | 4089 | 3809 | 280 |
| FG-2A | 12223 | 11847 | 376 |
| FG-Stress | 4390 | 4390 | 0 |

Metadata flags include chained-info bit 4 observations; no chain contents or semantic validation in this round. VMR rack has 26,853 runtime records; unique unwind-header locations 13,583. Evo PE32 has 253,952 executable mapped file bytes and no applicable x64 unwind coverage metric. Its previous relocation-backed import findings are preserved, no new instruction decoding. Uncovered bytes may include leaf code, padding or other regions; not dead code. The 595 FG-2A locally reached spans unconfirmed from enclosing starts are still unresolved. No new proprietary DSP equations.

Five local regression tests and four locally compiled owned PE cases passed (x86/x64, O0/O2). Exact tested source hashes recorded; CI reproduction added. No JUCE/UI/VST3 integration; research only. New CI pending.
