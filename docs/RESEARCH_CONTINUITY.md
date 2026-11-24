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

## Persistent reconciliation cache and actual analyzer comparison

Predecessor 23e69b54f4bf73dfbb9d295373f579a987c8e56b: Ghidra CI 45421739202 passed; static CI 45421739162 failed three tests because benchmark numeric regions collided with the equation schema. Corrected benchmark field to region_count, added report_kind; historical measurements unchanged, old version retained in Git history. Regression ensures the report is not read as equation evidence.

Added opt-in local cache: python -m skell_vst_decompiler.verification reports --cache-dir local/evidence-cache. Keys cover exact report bytes, set of filenames, verifier/index/cache source bytes and Python version. Atomic replacement, bounded cache reads and digest validation; corrupt entries recompute. External Revenant inputs are still read separately. No disk eviction yet; cache trusted local workspace only, not a security/authenticity mechanism. Initial output order differed on cache hits; corrected by sorting CLI JSON keys. CLI miss/hit output now byte-identical. Local restored lab subset 82 tests passed. Benchmark on 26 restored reports, 30 repetitions: median 3.074 ms uncached vs 1.314 ms warm, equal results (about 2.34x). This excludes engine execution and is not a full repository benchmark.

Actual GNU and LLVM objdump ran on a freshly compiled owned PE, both found the expected direct call at 0x102f to 0x1000; source fingerprint recorded in reports/engine_cache_validation_2026-11-24.json. Explicit agreed_static, single_observation, conflict states; mismatched fingerprint/scope rejected. Missing observations are not proof of absence. New CI step repeats the owned fixture comparison. Ghidra previously verified separately; Revenant and Rizin still not run. New full CI pending. No production DSP or vendor binaries changed.

## External-engine batch cache and bounded parallel execution
Verified predecessor dc9156496fd30c6279ed7f80dc5142bca2bc03ff: static CI 45423267799 and Ghidra owned-fixture CI 45423267668 passed. Added engine_batch.py; existing interfaces preserved. GNU and LLVM run in one or two worker threads over up to 64 bounded scopes. Each observation cached by exact source, scope, analyzer executable hash/version/path, implementation hashes, Python version and explicitly supplied environment ID. Shared-library/environment changes require a new ID. Cache trusted local only, no eviction yet. Do not modify executables during a batch. Agreement preserves per-engine evidence and distinguishes full/partial agreement, single observations and conflicts; no confidence scores interpreted as correctness probabilities.
 
Two actual owned-fixture runs: each 38 analysis jobs across 19 overlapping bounded ranges, all warm cache hits, exact observations across serial/parallel/cached runs, environment ID invalidation and corrupt-entry recovery tested. First run 203.634 ms serial / 88.999 ms parallel / 44.848 ms warm; second 133.606 / 88.879 / 51.793 ms. This is a small fixture workload, not 19 independent algorithms or full decompilation. Local restored suite 84 tests passed, native original dynamics and space regression passed across four sample rates; space benchmark 60.0477 ns/frame (single observed run). No new reference audio or vendor DSP analysis. All four new source/test blobs checked against locally generated hashes. New static CI adds actual batch smoke; separate checksum-pinned Rizin v0.9.1 owned-fixture workflow added, execution pending. Local network DNS lookup failed; no installed Rizin or Docker/Revenant. Actual Revenant and Ghidra/Rizin unified comparison remain milestones, not completed.

## Unified CI execution — same owned binary
Verified predecessor eee476982f1e3f7a33e036cd113b1c4413812f4f: static CI 45424076890 passed 92 tests plus native DSP and GNU/LLVM batch; Ghidra CI 45424076693 passed two functions and three links; real Rizin CI 45424076949 passed with 2 exact unwind starts and 1 function without an unwind record, zero non-executable entries. CI batch 38 warm hits, 463.566 ms serial / 333.103 ms parallel / 34.831 ms warm. The prior smoke workflows used separate compiled fixtures; do not compare addresses across different fingerprints.

Added multi_engine.py and unified_engine_smoke.py plus separate CI workflow with checksum-pinned Ghidra 12.2, Rizin 0.9.1, radare2 6.2.6, Revenant v0.1.0 source commit ec81fc0ddecfa736494d9cb365adf6edccbfc41b. Same owned PE for all. Function entry claims compared across Ghidra/Rizin, positive function call edges across Ghidra/GNU/LLVM; GNU/LLVM direct site equality separately asserted. Revenant deterministic static pipeline (provider none, only recon/triage/extract/disasm) reports metadata, not a vote on individual call sites. No private originals or pseudocode in CI. New workflow and regression test implemented, not yet run/verified. Local execution not required for this batch; use exact-head CI logs. No new vendor DSP evidence.
