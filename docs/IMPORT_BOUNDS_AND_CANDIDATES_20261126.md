# Ordinary import bounds and register-import candidate evidence — 2026-11-26

Parent af6d6b6f64da216d7fe9e46deed563e9e83cceae. Exact prior CI at commit time: Python static-analysis tests: in_progress; Independent PE oracle (owned fixtures): success; Craft Anything metadata (owned fixtures): success; Reccmp export comparison (owned fixture): success; Real Rizin smoke (owned fixture): success; REA PE imports (owned fixtures): success; Real Ghidra smoke (owned fixture): success; Unified engines (owned fixture): success. Preserve previous research and reports.

## Parser defect and repair
Previous PE.imports() did not honor NumberOfRvaAndSizes, the declared directory size, or the original file-backed IAT slot on every entry. This could incorrectly consume extra descriptors. New audit_imports() validates directory count, declared descriptor size/alignment/bounds, IAT slot, duplicate slots, hint bytes, reserved ordinal bits and nonempty names; existing imports() identity-map API is preserved. An explicitly labeled compatibility path accepts exactly one immediately adjacent all-zero descriptor, not additional nonzero descriptors. Microsoft PE format documentation https://learn.microsoft.com/en-us/windows/win32/debug/pe-format (data-directory and import lookup descriptions) informs validation. Ordinary file metadata only, no loader or protection bypass.

All 44 exact prior fingerprints replayed. Every ordinary slot identity (DLL and symbol) agrees with the old parser, 26,466 total. 41 use a null inside declared directory; three (MB MixHead, VT-5, SSL Stereo Image) have exactly one adjacent null descriptor, outside declared size. Their layout is reported, not silently normalized. No change to prior delay-import census.

## Bounded dependency improvements
BoundaryAudit supports byte-checked redundant REX.W for normal RIP-relative FF /2 and /4. Adds adjacent MOV r64,[RIP+disp32] then CALL/JMP same register recognition: both decoders, exact load/branch bytes, full instruction extent and known import slot must agree. Report separately as candidate, not resolved execution; intervening instructions, different register, wrong displacement or truncation rejected. No general virtual-dispatch resolver and no protected-code analysis.

Replayed all 114 prior containing ranges: identical 74 import boundaries, one rejected transfer, zero new adjacent candidates. This is a negative actual-corpus result, not new vendor DSP evidence. Existing 147 dynamic sites and the 74 GNU-side/15 LLVM-only discrepancies from earlier different 91-scope replay remain open. No new Auto-Key processing or protection analysis.

## Verification
Seven local unit tests passed (four new cases plus three earlier boundary tests) using owned clang/lld-linked PE fixtures. New cases include malformed descriptor bounds, header directory count, adjacent-null compatibility, unbacked IAT and reserved ordinal bits, prefix and adjacent import-register candidates with negative controls. Exact four tested source/test blobs verified before commit. Full new CI pending. No third-party code or binaries committed, no audio or production changes, no UI changes. No JUCE build required for this static Python-only batch.

See reports/native_scoped/import_bounds_candidate_replay_2026_11_26.json.
