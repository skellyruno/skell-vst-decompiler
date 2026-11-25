# VMR — corpus-wide shared-code triage (2026-11-25)

## Provenance and corpus integrity

Used the exact owner-supplied Google Drive `VMR_SPLIT_FOR_CHATGPT` four-part archive, already reconstructed and verified at ZIP SHA-256 `353f23373ac05d7b2121c313073f08c708e879d839115d4ce5d30657732f481e` (795,482,157 bytes; 899 archive entries). The separately extracted 31 `.epl` Windows x64 engines were rehashed on intake. The code and portable JSON report contain **only counts, source fingerprints, candidate RVAs and findings**, never binary bytes or proprietary source.

## New verified static finding

Across **31 engine modules**, enumerated x64 PE unwind records and SHA-256 hashed entire executable spans with lengths **32–4096 bytes**. This is a bounded index, not complete executable-code coverage: leaf functions may lack unwind records, and functions exceeding 4096 bytes are excluded. Results:

- **487,363** eligible unwind-covered executable spans.
- **330,919** distinct span fingerprints.
- **2,849** fingerprints present in *all 31 modules*.
- **3,821** fingerprints present in at least ten different modules.
- **147,030** scoped span occurrences in this ten-module-or-more category, **30.17%** of scoped occurrences.
- Matched-region spans sum to **48,008,721 bytes** across module occurrences, *not* unique implementation bytes.

This provides direct evidence of substantial recurring code across the VMR family. It does **not** prove that those regions are non-DSP or share the same source implementation; even exact byte-identical code may be reusable DSP.

The highest-similarity pairs among the sampled bounded regions are VCC Channel / VCC MixBuss (5,264 common distinct spans, Jaccard 0.219370); Hollywood / New York (4,378, 0.177823); Hollywood / London (4,369, 0.177393); FG-116 Modern / FG-116 Vintage (4,303, 0.175225); FG-N / FG-S (4,102, 0.168890); and Gate Classic / Gate Drums (3,904, 0.156504). These exact binary-region correlations help **prioritize investigative pairs**, not infer sound parity.

## Previous native-scoped targets re-checked

15 selected previously researched bounded regions in FG-401, AirEQ Air, VCC Channel, VCC MixBuss, FG-116 and FG-2A each had corpus module frequency **one**. These are investigative anchor scopes, not new runtime-confirmed algorithm descriptions. Their uniqueness is a property of **exact compiled bytes**. Relocation and compiler effects can make analogous algorithms differ bytewise; unique binary bytes do not establish unique DSP.

## Tooling implemented

`skell_vst_decompiler/shared_code.py`: bounded 2–64-module, up-to-1GiB local `.epl` corpus; exact source fingerprints, per-module summary, shared-function frequency and top family pair analysis. Optional expected name/size/SHA inventory before scanning. No binary execution, side-effecting writes or source code extraction. It retains private region-level hashes only in memory.

`dsp_job --shared-corpus <local-directory>` now optionally annotates existing Find DSP candidates by shared-code frequency, preserving original candidate scores and order. If a target is absent from the selected corpus, it fails explicitly rather than inventing a comparison. Existing no-corpus behavior and version-0.2.0 Analyzer plugin identity are unchanged; no UI work this batch.

**Owned-fixture regression:** 3 real Clang/LLD PE32+ DLLs containing identical shared and deliberately different original C++ functions were built but **never executed**; common function fingerprints and unique functions identified. The original floating-point fixture initially failed to link (`_fltused`), fixed explicitly; optimized leaf functions initially lacked unwind metadata, fixed with calls plus `-funwind-tables`. Unit tests cover source integrity, symlinks, budgets, duplicate handling, unchanged candidate scores and explicit errors. 

Local tests: `python -m unittest tests.test_shared_code tests.test_dsp_job -v` and `PYTHONPATH=. python tests/shared_code_smoke.py` passed. Local *full exact repository* suite is unavailable because the local archive predates the active GitHub head; use current-head CI for release gates. A local end-to-end VMR job used a **test-only, limited fallback discovery adapter** due to the older archive; its successful shared-code annotation is not full class-anchored discovery verification. Exact-head CI pending on commit.

## Priorities

1. Use cross-module evidence to prioritize previously verified DSP candidates, not exclude shared code automatically.
2. Add source-known utility-versus-DSP classification across independent owned plugin functions and compiler configurations.
3. For VMR, follow parameter readers through mode-conditional dispatch into sample processors and coefficient setters; resolve indirect references.
4. Use authorized host behavior only when the real plugin and sandbox/host are available and separately verified.
5. Continue TVB/Gem/A1TriggerGate unresolved endpoints; preserve old reports.

## Commands

```sh
python -m skell_vst_decompiler.shared_code '/private/VMR/modules' --inventory reports/rack_intake/vmr_inventory.json
python -m skell_vst_decompiler.dsp_job --binary '/private/VMR/modules/FG-401.epl' --shared-corpus '/private/VMR/modules' --output '/private/reports/FG401_shared.json'
PYTHONPATH=. python tests/shared_code_smoke.py
```
