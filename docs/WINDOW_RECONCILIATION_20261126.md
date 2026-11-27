# Cross-window evidence reconciliation — 2026-11-26

Parent 3addeb899a66f51f6c0f5b503ff563e46fe7d678. Parent CI: all eight workflows completed successfully. All eight original fingerprints, 479 recorded scope hashes, and earlier transfer-triage denominators reverified. Cached Quick4 manifest passed all 13 checks. New raw-row consensus is limited to existing windows; no destination-driven disassembly or execution.

## Results

| Target | Windows | Unique transfer sites | Direct | Indirect memory | Indirect register | Unclassified | New guards | Retained local value-flow candidates | Boundary conflicts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| StandardCLIP | 41 | 795 | 758 | 32 | 5 | 0 | 2 | 35 | 0 |
| Trackspacer | 42 | 1078 | 1029 | 45 | 4 | 0 | 4 | 60 | 0 |
| FG-2A | 44 | 1277 | 1225 | 43 | 8 | 1 | 14 | 205 | 4 |
| Panagement | 77 | 2477 | 2404 | 63 | 10 | 0 | 16 | 99 | 0 |
| DeeDoubler | 43 | 1894 | 1839 | 41 | 14 | 0 | 4 | 89 | 0 |
| VT-5 | 78 | 2304 | 2053 | 226 | 23 | 2 | 2 | 90 | 36 |
| SSL Fusion Stereo Image | 76 | 3310 | 3149 | 146 | 13 | 2 | 6 | 64 | 50 |
| MixHead | 78 | 1906 | 1730 | 170 | 6 | 0 | 3 | 50 | 0 |
| Total | 479 | 15041 | 14187 | 766 | 83 | 5 | 51 | 692 | 90 |

No repeated transfer observations were found within this corpus. Prior local guard sets were retained, and 51 receiving-window guard observations added only at existing common raw and linear decoder instruction starts. All 692 previously retained local value-flow candidates survived. No other existing window establishes a common raw start at any of the 90 disputed destinations. These conflicts remain unresolved.

Six of the prior 11 unclassified transfer forms were reconciled as redundant REX.W textual rendering differences (four indirect memory, two indirect register); both raw rows must agree and the explicit prefix annotation and normalized operand text must match. Existing indirect-kind validation still does not independently verify full memory operands. Remaining five unclassified forms: four unusual prefixed conditional branches and one missing raw decoder row. No inferred target is accepted for those cases. The 854 unresolved destinations remain unchanged (849 classified indirect, five unclassified).

## Implementation and verification

New original window_reconcile.py accepts raw maps from bounded windows of one exact binary. It rejects overlapping raw rows, excludes conflicting or missing transfer observations in overlapping source windows from guard propagation, and counts candidate sites once per binary. Receiving-window guards are added only after dual-decoder raw start checks; the local replay additionally requires both linear decoder starts. The input fingerprint, scope digest and prior denominator checks occur in the corpus replay driver, not in the pure window reconciliation function. This is evidence validation, not whole-binary control flow or runtime execution.

Six new targeted unittest methods passed, including an independently compiled Windows PE fixture demonstrating an external-to-window branch entering mid-chain and eliminating a misleading local path, duplicate observations, conflicting/missing source evidence, boundary conflict preservation, and redundant-prefix positive/negative cases. Thirteen previous targeted methods also passed, total 19/19. Exact tested source and test Git object hashes verified. Current-head full CI is unverified. Local full per-window report SHA-256: cdbcaab48d6c6d22efbfc5a1d6dfc18c3dedb879c014ab93d0e5e40af1197ab9. Earlier findings and reports retained. No vendor execution, protection analysis, new target traversal, private audio, vendor implementation or production changes. No DSP equation or audio equivalence claim.
