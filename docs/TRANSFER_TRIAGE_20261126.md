# Direct-transfer backlog triage — 2026-11-26

Parent dc2d54631cfcb2652dec9c47d3573f06678688ec. Replayed all eight exact binary fingerprints and 479 scope hashes and reproduced every prior transfer-classification denominator. Quick4 cached manifest 13/13 passed. Prior local source dependencies match their recorded Git blobs. This pass corrects the gap in inference from the next printed instruction address: both actual decoders now emit raw instruction bytes and each retained row is checked against the original bounded bytes. Only ordinary complete relative transfer forms and count-register short branches are accepted for direct targets. Indirect forms are classified by ordinary opcode/addressing length and operand kind (register identity checked for register form), never by a resolved target. No additional target windows are decoded.

## Results

| Target | Prior unresolved | Direct recovered | Indirect memory | Indirect register | Other / raw disagreement | Prior boundary conflicts |
|---|---:|---:|---:|---:|---:|---:|
| StandardCLIP.vst3 | 48 | 11 | 32 | 5 | 0 | 35 |
| Trackspacer25.vst3 | 58 | 9 | 45 | 4 | 0 | 60 |
| FG-2A.epl | 60 | 8 | 43 | 8 | 1 | 209 |
| Auburn Sounds Panagement 2-64.vst3 | 81 | 8 | 63 | 8 | 2 | 99 |
| DeeDoubler.vst3 | 62 | 7 | 40 | 14 | 1 | 89 |
| MixWave DW Fearn VT-5.vst3 | 266 | 15 | 225 | 23 | 3 | 126 |
| SSL Fusion Stereo Image.vst3 | 178 | 17 | 144 | 13 | 4 | 112 |
| MB MixHead.vst3 | 188 | 12 | 170 | 6 | 0 | 50 |
| Total | 941 | 87 | 762 | 81 | 11 | 89 |

The previous 941 unresolved observations partition into 87 newly byte-verified direct transfers, 843 ordinary indirect form classifications and 11 other unresolved observations (10 unsupported/discordant forms and one raw span not reconciled). The remaining 854 have no verified destination; indirect classification is not target resolution. Of the 87 direct observations, 30 have an existing common in-window start, 56 land outside the selected window (not followed), and one adds a boundary conflict. There are 15 additional distinct-per-window guard entries, and the previously retained 692 local candidate stores remain unchanged after replay.

## Boundary conflicts

Of the 89 prior noncommon-boundary observations, 85 targets are interior to a printed raw span under both decoders, one is interior in GNU and uncovered by LLVM, two are a GNU start but interior in LLVM, and one is a GNU start but uncovered by LLVM. These are descriptions of existing printed rows, not proof of alternate instruction streams or valid entrypoints. The newly identified direct observation adds one conflict (90 total). Neither conflicting destinations nor indirect targets were followed. The discrepancy is preserved, not forced into a common boundary.

## Validation and reproducibility

New original transfer_triage.py separates ordinary indirect forms, complete window-end transfer encodings and count-register branches from unresolved cases. Its four new test methods plus nine prior methods ran locally and passed (13 total), including real owned PE fixture built with clang/lld-link and both GNU and LLVM. Initial LLVM --show-raw-insn option failed on installed LLVM; fixed by using its default raw output and reran. Exact tested source/test blobs verified. Parent CI last observed seven successful and Python in progress; new head CI unverified. Machine-readable aggregate at reports/native_scoped/transfer_triage_2026_11_26.json; full local per-window report SHA-256 ef58d36fe4f2ed66813924bfc42a28292ce8c871cf56059235432bc7d864476b. To replay, use the previous report's exact binary fingerprints and scope hashes, compare disassemble() outputs and raw_decode() rows only inside those scopes, then use triage() and value_flow.scan() with the union of accepted entry guards. No vendor code, raw constants, private audio, protection bypass, production DSP, preset or UI change. No recovered DSP equation or runtime equivalence claim.
