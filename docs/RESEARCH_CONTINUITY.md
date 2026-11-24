# Research continuity — 2026-11-24

This is the continuation checkpoint for the existing private research branch, not a replacement project.

- Active draft: https://github.com/skellyruno/skell-vst-decompiler/pull/1
- Branch: feature/native-dsp-evidence-core-20261123
- Verified predecessor: d872b3795423b7d891a0ad029935c3bbd1d4f411
- Previous static tests: https://github.com/skellyruno/skell-vst-decompiler/actions/runs/45418372570 — success
- Previous real Ghidra owned-fixture smoke: https://github.com/skellyruno/skell-vst-decompiler/actions/runs/45418370886 — success
- Earlier evidence audit commit 01c98354ff260e0d2bcbe35e9741f916e5868ba6 passed both workflows.

## Preserve existing work

Read docs/DSP_EQUATION_ATLAS.md, docs/MULTI_ENGINE_CLASS_NAVIGATION.md, docs/VMR_VARIANT_NAVIGATION.md, docs/EVIDENCE_AUDIT.md and the relevant exact-source reports. The atlas has 128 prior evidence records (not full functions or algorithm completion). Class navigation includes 17 TVB classes, six VMR classes, 24 vtable records and 23 selected addresses. The paired VMR report contains six wrappers and 36 sampled table entries. Preserve the original lab exports and earlier results; update additively.

The previously delivered Skell_VMR_Variant_Navigation.json is now archived verbatim at reports/vmr_variant_navigation.json. SHA-256 b408003f878e38c0726c761b58e316d96844ce304b638b6939ba7ee98c65857d; Git blob 2b91ab4b8828aacfbf7fcc4a4552bfcb3b4d4d8f. The attachment-to-Git blob comparison matched exactly. Historical navigation findings remain distinct from equation claims and runtime verification. Never silently revise this snapshot; create a new versioned report if evidence changes.

## Source restoration

TVB Rack V2.vst3 and Virtual Mix Rack.vst3 were located in the private Library. VMR archive was reconstructed previously from four parts in the private Drive folder VMR_SPLIT_FOR_CHATGPT. Its SHA-256 was reported as 353f23373ac05d7b2121c313073f08c708e879d839115d4ce5d30657732f481e. Module SHA-256 values are in reports/class_navigation_summary.json and reports/vmr_variant_navigation.json. Re-materialize only authorized private originals as needed, verify every fingerprint before using an RVA, and do not request reuploads before checking the Library and existing Drive segments. Local session paths are not persistent.

## Next work

Keep the existing private read-only analysis and original DSP experiments separate. Extend evidence validation and compare independent analysis results only where authorized. Prioritize report-level contradictions and reproducible original DSP tests; do not treat inferred routine roles, runtime dispatch, or proprietary audio parity as established. See docs/UPSTREAM_TOOL_REVIEW.md for external tool decisions. No new vendor execution, binary analysis, or production DSP changes in this continuity batch.

At each handoff, record the current commit, exact-commit CI result, changed paths, new findings and unresolved questions. Latest CI for a new commit must be checked separately; no successful test should be inferred from its predecessor.

## Evidence reconciliation and Revenant interface

Verified predecessor: ea5febfd3577727f8df89b449c42bfdb40bb192e. Static CI run 45420118958 and real Ghidra owned-fixture smoke 45420118911 succeeded. Independent cross-report recomputation using eight VMR source reports (64 regions) and the archived snapshot reproduced all six overlap results: 3,0,3,0,6,0. Archived attachment SHA-256 independently rechecked locally. This is report consistency, not fresh binary analysis.

Added skell_vst_decompiler.verification: exact input digests, deterministic dependency key, mismatch reporting, range and duplicate checks, offline Revenant report metadata importer. Six local synthetic tests passed; seventh repository-wide test added for CI. No new vendor binary execution or DSP behavior claims. Exact new CI pending. Future work: owned-fixture Revenant runtime smoke, then authorized external metadata comparisons. No persistent disk cache implemented yet; input key is the groundwork.

## Indexed evidence verification
Verified predecessor 69f91f4a45471184724d34c08e7e8c5695d754ac: static CI run 45420857710 and real Ghidra owned-fixture smoke run 45420857450 succeeded. New IntervalIndex integrated into the existing verifier; all old output semantics retained. Nine local tests passed (six previous synthetic verifier tests plus three new index tests), including 1,000 seeded queries compared with the linear oracle. Local baseline verifier Git blob matched the predecessor exactly. Benchmark: 40,000 synthetic regions, 500 queries, three runs; median linear 0.841050492 s, indexed including build 0.014512170 s, outputs equal. Worst-case nested ranges can still require a linear scan within one fingerprint; performance is not a global guarantee. Reproduce with PYTHONPATH=. python benchmarks/interval_index_bench.py. Report at reports/interval_index_benchmark_2026-11-24.json. No real binary decompilation speed or audio improvement measured. New full CI pending. New upstream reviews are appended in UPSTREAM_TOOL_REVIEW.md; no engine replaced. Next: owned-fixture external engine smoke and persistent caching with invalidation tests.
