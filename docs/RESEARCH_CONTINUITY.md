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
