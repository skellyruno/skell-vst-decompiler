# Ordinary dependency boundaries and delay-load parser — 2026-11-26

Previous exact commit 377445841645fe4d04ae638a7be095503525b19a passed all eight workflows. This static-only batch extends ordinary PE dependency identification, not recovery of protected or dependent vendor implementations. No vendor code/binary uploaded, executed or reconstructed.

## Findings
44 active source modules matched the previously recorded corpus fingerprints. Read-only import census: 26,466 ordinary import slots (per-module occurrences), zero RVA delay-import slots on this corpus. Inspect 114 selected bounded containing ranges across 41 modules (62 prior VMR wrappers plus 52 standalone scopes). This scope set differs from the prior 91-region replay, so totals are not a reduction of the earlier unresolved indirect sites.

1,283 transfers terminate at local entries, 74 at identified external imports, four outside file-backed executable sections, one decoder/byte disagreement rejected. 70 external boundaries through one jump, four through three. Local-entry classification is not a confirmed function boundary or DSP role.

Brauer Motion: 36 external boundaries, including 23 calls/jumps reaching WavesLib1_15.0.70_Win64.dll and 13 ordinary CRT/runtime calls. Panagement: eight Kernel32 boundaries. VT-5: 11 runtime/math/heap boundaries including six CRT math. TVB: 19 ordinary boundaries including 13 CRT math. These identify library responsibilities, not hidden implementation or live addresses. All 31 VMR wrapper pairs examined; no import boundary among their 248 supported direct transfer sites. Dynamic indexed calls remain unresolved. Auto-Key, MixHead and StudioRack metadata-only; no protection bypass, and no new key-detection equations.

## Tool and validation
Added boundary_paths.py with bounded RVA-based PE32+ delay descriptor reader, ordinary/delay import collision checks, exact E8/E9/EB and FF15/25 byte-derived transfer destinations, GNU/LLVM text agreement, bounded ordinary jump-following, cycle/limit detection and conservative stop on unresolved pointers. Unsupported prefixed transfers and dynamic object dispatch intentionally not resolved. Three local tests passed including actual clang/lld-linked delay-import fixture, two-hop import chain and malformed descriptor rejection. Tests are discoverable by existing unittest CI. Exact tested blobs verified. Full new CI pending. Local JUCE DNS failed; no UI/production modifications. Previous decoder disagreements and 147 dynamic sites remain open; no 80% claim.

Report: reports/native_scoped/dependency_boundary_audit_2026_11_26.json.
