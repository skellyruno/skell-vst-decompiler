# Entry-guarded local value flow — 2026-11-26

Parent a0de21184d5546ff447207d64f6eebf41be1a934. Parent CI 8/8 passed. The previous bounded-value-flow work is already on the existing draft branch. This pass reuses its exact local report, rechecks all eight binary fingerprints and 479 scope hashes, and reproduces every limit-16 baseline result. Cached Quick4 kit manifest 13/13 passed; no UI or JUCE build needed for this Python-only research.

## Correctness issue and change

A contiguous instruction stream can include a destination of a direct transfer, so a preceding load may not have executed on all incoming paths. The new original flow_guards.py validates complete ordinary unprefixed relative CALL/JMP/Jcc byte forms and both decoded destinations. Observed common-boundary in-window targets reset local origins in value_flow.scan when requested. Default behavior remains backward-compatible. This is not a whole-binary CFG; indirect transfers, external incoming edges, unsupported encodings and noncommon instruction boundaries remain unresolved. A second optional mode permits exact single-byte NOP and byte-checked register-only CMP/TEST; all unknown instructions, memory comparisons, pointer mutations, branches and stores remain barriers.

## Results

| Target | Windows | Baseline | Guarded | Removed |
|---|---:|---:|---:|---:|
| StandardCLIP.vst3 | 41 | 35 | 35 | 0 |
| Trackspacer25.vst3 | 42 | 60 | 60 | 0 |
| FG-2A.epl | 44 | 233 | 205 | 28 |
| Auburn Sounds Panagement 2-64.vst3 | 77 | 99 | 99 | 0 |
| DeeDoubler.vst3 | 43 | 89 | 89 | 0 |
| MixWave DW Fearn VT-5.vst3 | 78 | 90 | 90 | 0 |
| SSL Fusion Stereo Image.vst3 | 76 | 64 | 64 | 0 |
| MB MixHead.vst3 | 78 | 51 | 50 | 1 |
| Total | 479 | 721 | 692 | 29 |

10,688 verified transfer-site observations land at 7,872 distinct-within-window common boundaries (counts can overlap across scopes). Another 3,323 verified destinations are outside their source window, 89 in-window destinations lack a common decoded boundary, and 941 transfer candidates remain unresolved. These counts include repeated destinations and selected scope overlaps, not unique whole-binary edges. 29 prior candidate stores excluded by the stricter rule across six windows: FG-2A 28, MixHead 1. Remaining 692 counted stores in 82 windows: 394 same-expression, 298 different-expression, 12 within previously shared-shape-flagged windows. Same expressions do not prove runtime address identity. No additional corpus paths from the optional transparent-instruction mode, although the owned positive fixture demonstrates its effect. Do not interpret exclusions as proven unreachable or false DSP.

## Verification

Nine local unittest methods actually ran and passed (three new and six prior), including real owned Windows PE builds with clang/lld-link and GNU/LLVM decoders. Positive and negative controls include a branch entering mid-chain, safe register-only comparisons/NOP, pointer mutation and memory comparison barriers, condition aliases, malformed relative encodings and mismatched operands. Exact tested Git blob IDs matched. New full CI unverified. Safe summary with six changed window hashes in reports/native_scoped/guarded_value_flow_2026_11_26.json; complete local report SHA-256 7d6cdd58396a855ca7da340537132cc06246c7e23467ed3b8d944d5092119b88. All prior reports retained. No vendor execution, protection analysis, raw vendor values, reconstructed implementation, production DSP, preset, SkellCore or UI change.
