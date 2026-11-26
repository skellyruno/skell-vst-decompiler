# Full-scope consensus and ordinary math boundaries — 2026-11-26

Parent c9e85ff9c17177d5f3d48e90cac3c3d4df997eb3. All eight parent CI workflows passed. All eight exact original fingerprints and 47 prior scope hashes verified locally, including FG-2A recovered from the two verified archive parts. Quick4 archive checksums 13/13 pass. Current PE and disasm dependency Git hashes matched. No UI change or JUCE build necessary for this static Python research.

## Analysis changes
Original scope_consensus.py reconciles both decoders by address, mnemonic and inferred span from consecutive in-window addresses. It deliberately excludes terminal sites, duplicates, overlong spans and disagreement. Narrow scalar/packed floating-point and x87 categories extend the previous interval-only census. Unit tests cover family selection, duplicate and mismatched instruction sites, terminal arithmetic exclusion and a locally compiled owned Windows PE fixture. Three local test methods passed after fixing the excluded-terminal accounting. Exact source/test Git blob IDs match. No independent instruction-length decoder or runtime proof.

## Results
16,795 matching scoped instruction sites, 70,623 inferred span bytes; 57 mnemonic disagreements, 12 span disagreements, 18 one-decoder-only sites and 47 terminal-unbounded sites excluded. 1,136 distinct selected arithmetic sites; 971 inside prior branch intervals and 165 outside. These counts describe only the previously selected 47 scopes. No new candidate anchors established.

| Module | Agreed sites | Selected arithmetic | Outside prior intervals | CRT math imports | Direct math calls |
|---|---:|---:|---:|---:|---:|
| StandardCLIP.vst3 | 2375 | 60 | 15 | 0 | 0 |
| Trackspacer25.vst3 | 2491 | 268 | 67 | 0 | 0 |
| FG-2A.epl | 2516 | 667 | 9 | 30 | 36 |
| Auburn Sounds Panagement 2-64.vst3 | 774 | 0 | 0 | 0 | 0 |
| DeeDoubler.vst3 | 878 | 121 | 56 | 0 | 0 |
| MixWave DW Fearn VT-5.vst3 | 3970 | 14 | 14 | 36 | 6 |
| SSL Fusion Stereo Image.vst3 | 3253 | 6 | 4 | 0 | 0 |
| MB MixHead.vst3 | 538 | 0 | 0 | 34 | 0 |

FG-2A: 665 scalar double and two packed-double arithmetic sites; 36 ordinary math call sites across all selected scopes rather than 20 in a single generator. Trackspacer: mixed precision and packed single arithmetic, 67 selected sites outside previous intervals. DeeDoubler: 56 outside previous intervals. StandardCLIP: 43 single and 17 double scalar sites across selected scopes. VT-5: 14 arithmetic sites outside intervals plus six verified roundf calls, not EQ topology. SSL: six matching sites (four double scalar, two x87), not stereo matrix. Panagement and MixHead remain weak anchors; zero selected arithmetic does not imply absence of DSP. MixHead has 34 selected CRT math import slots, no matched direct thunk calls in its chosen regions.

## Ordinary math boundary census
Allowlisted standard mathematical symbol names in api-ms-win-crt-math-l1-1-0.dll only. Reused bounds-checked ordinary import parser, matched E8 rel32 targets under both decoders and original displacement bytes, verified single FF25 RIP-relative import thunk and IAT identity. 100 selected ordinary math slots, 42 matched direct call sites: FG-2A 36 and VT-5 6. Does not include inline math, alternative libraries, register calls, other thunks or runtime execution. Reused existing selected scopes; no protection, activation, or licensing paths examined. The full local aggregate scope report is identified by SHA-256 in the machine-readable summary; no vendor values, disassembly listings, reconstructed implementations or private audio uploaded.

## Outstanding
No clipping transfer curve, spectral attenuation law, optical dynamics, modulation route, crossfade control law, EQ topology, stereo matrix or tape model proven. This is an evidence-quality improvement and a better prioritization of current scopes, not a new processing engine. Production DSP, presets, SkellCore and UI unchanged. New full CI pending.
