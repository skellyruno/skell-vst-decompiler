# Bounded static-flow audit

The previous exact commit e265f40a99e1ff12b723e278b8b5019070d99ead passed 148 tests and eight workflows. Six original input hashes and the archived atlas blob matched; the VMR split archive SHA-256 matched before extraction. GNU/LLVM source-byte agreement is required. All 128 historical DSP range starts are used as local seeds, not established function entries; a separate public export-derived seed is used in each rack and Evo. The model follows bounded relative jumps and both conditional arms, assumes calls return without following them, stops at unresolved indirect jumps and unsupported forms, and records missing/interior/out-of-scope destinations. It is an approximation, not a full x86 control-flow analysis or proof of runtime reachability.

| Scope family | Agreed spans | Reached in model | Not reached | Scopes with unverified boundary |
|---|---:|---:|---:|---:|
| TVB (64) | 4831 | 4731 | 100 | 3 |
| FG-116 (8) | 1082 | 1050 | 32 | 1 |
| FG-2A (50) | 2846 | 1890 | 956 | 9 |
| FG-Stress (6) | 1001 | 1001 | 0 | 1 |

Overlapping scopes are summed, not deduplicated. FG-2A has the largest unresolved difference; not-reached spans may be reachable via alternate entries, indirect branches, exceptions, or paths outside these bounds. All 128 seeds were agreeing instruction starts, and no traversed flow destination landed in the interior of an agreeing span. This does not establish function extents or complete DSP routing.

The initial audit stopped at the first two-byte instruction in both VST3 factory windows: GNU printed a REX prefix token while LLVM printed the stack operation. A narrowly scoped x64 push/pop alias rule corrected this; x86 and mismatched-mnemonic controls remain rejected. Six local unit tests and four locally compiled owned PE fixture cases passed. TVB public window reaches 23 of 63 spans and observes three untraversed direct calls; VMR reaches 43 of 43 with three out-of-window flow destinations. Evo public window reaches 31 of 67; repeating with its whole 212992-byte executable section yields the same 31 of 73581 spans, with one direct call to an agreeing start left untraversed. No implication that surrounding code is dead. Private aggregate report retained, no vendor bytes/pseudocode or private source uploaded. Latest CI pending.
