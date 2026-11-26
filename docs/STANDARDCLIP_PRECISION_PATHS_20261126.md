# StandardCLIP precision-path and denormal handling evidence — 2026-11-26

Parent 781c65e821d2df20dbf82566bb979eb06fa24d89; previous exact-head CI 8/8 passed. Source SHA-256 matched the prior StandardCLIP fingerprint. Read-only inspection; no vendor source, coefficient arrays, binary, private audio, licensing or protection analysis published.

## Findings

- Four previously identified entry thunks now have byte-checked direct jump targets and bounded wrapper bodies. All four contain one STMXCSR, an immediate OR with the standard FTZ/DAZ mask 0x8040, and two LDMXCSR sites. Local operand inspection supports save/change/restore on the ordinary path. This is not proof of restoration on every branch or exception.
- The two shorter wrappers reach separate packed/scalar addition leaf helpers. One contains four packed float add sites and five scalar float adds; the other contains four packed double adds and five scalar double adds. Local operands show a two-buffer accumulation pattern with scalar tail. These are vector utilities, not the clipper itself.
- Four contiguous unwind-linked helper families show paired ring/buffer bookkeeping and route to distinct copy-like helpers. Two further helper scopes contain bounded channel/count selection and 4-byte versus 8-byte address/length scaling, each calling the same lower-level routine. Three scale checkpoints per helper were corroborated by both decoders and original bytes; lower-level routine not semantically identified.
- Across 16 windows: 1,910 address/mnemonic agreements (GNU 1,915 sites, LLVM 1,917), 49 separately verified direct rel32 call/jump edges, 36 selected byte-backed floating-point opcode/mask sites. The additional six scale observations are separate, not added to the 36. These counts are not function/DSP coverage.

## Tooling

New original precision_audit.py uses existing PE reader and both disassemblers; checks fingerprint, executable scope bounds, selected x86 opcode forms and direct branch destinations from original bytes. The owned PE regression was compiled with clang/lld-link and decoded with both actual engines; positive mnemonic/mask/branch checks and wrong-fingerprint, oversized-range and negative-window checks passed. Exact local source/test blobs and unchanged dependency blobs matched. The report stores only bounded scope hashes, counts and selected relationship evidence. To replay, call audit_scope(PE(local_path), expected_sha256, start_rva, length) with each report scope. This is an opcode census, not complete operand verification or automated dataflow.

## Remaining work

Clipping transfer curve, oversampling ratio/filter architecture and online/offline control mapping remain unresolved. No new deep result for Trackspacer, DeeDoubler, Panagement, TVB/FG-2A, VMR, SSL/VT-5/MixHead, or Evo in this batch. Four reference files revalidated locally, no vendor executable loaded. No SkellCore production or UI changes. Quick4 offline kit retrieved and all thirteen manifest entries verified; no UI change requiring capture. Local targeted tests passed; full current suite and new CI remain unverified until completed.
