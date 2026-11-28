# Expanded arithmetic-anchor survey — 2026-11-26

Parent d7ee7fdfdcac266d75298e1136ca2a98fbbdfdcf; all eight parent CI runs passed. Eight exact binary fingerprints and 47 prior scope hashes reverified. FG-2A recovered from two separately checksum-verified available split archive parts; cached Quick4 archive manifest 13/13 passed. Current local PE, disasm, navigation and scope-consensus dependency Git blob hashes matched. No UI scope or JUCE build required.

## Method

Original anchor_survey.py extends discovery beyond the same 47 regions. Inventory 128,730 x64 unwind records; filter complete ordinary .text extents to 128..8192 bytes with no overlap with previous 47 windows. 54,953 eligible extents screened, 5,057 with at least four unaligned legacy SSE opcode markers. Markers are not decoded instructions. Three deterministic bounded lanes (RVA stratified, high raw marker count, high marker density) chose 432 extents / 588,196 bytes. The four weaker targets (Panagement, VT-5, SSL, MixHead) each receive 24 per lane; other targets 12. Two decoders reconciled 131,854 sites / 583,044 inferred span bytes, including 26,063 selected FP arithmetic sites. 347 mnemonic, 232 span, 250 one-decoder and 431 terminal exclusions. These are scoped counts, not coverage of logical functions or runtime execution.

| Target | Decoded extents | FP sites | >=8 FP sites | Shared-shape flagged | Remaining >=8 |
|---|---:|---:|---:|---:|---:|
| StandardCLIP.vst3 | 36 | 4058 | 25 | 0 | 25 |
| Trackspacer25.vst3 | 36 | 3258 | 25 | 5 | 20 |
| FG-2A.epl | 36 | 3351 | 24 | 4 | 20 |
| Auburn Sounds Panagement 2-64.vst3 | 72 | 3887 | 44 | 1 | 43 |
| DeeDoubler.vst3 | 36 | 1875 | 25 | 1 | 24 |
| MixWave DW Fearn VT-5.vst3 | 72 | 3570 | 48 | 14 | 34 |
| SSL Fusion Stereo Image.vst3 | 72 | 2970 | 50 | 17 | 33 |
| MB MixHead.vst3 | 72 | 3094 | 50 | 3 | 47 |

Panagement and MixHead previously showed zero selected arithmetic in their chosen earlier regions; now 44 and 50 extents respectively meet the deliberately simple eight-site threshold. These are arithmetic candidates, not confirmed LFO or saturation paths. Earlier filters, clipping and compressor evidence remains unchanged.

## Shared-shape control

Arithmetic density alone over-ranks common support code. Of 144 stratified regions, 9 meet the eight-site threshold, versus 144/144 marker-count and 138/144 density regions. This is an observed biased screening yield, not precision against a DSP ground truth. 23 groups (55 extents) with matching byte length and selected FP family histograms across different modules were checked using complete relative mnemonic and inferred span signatures under both decoders (terminal instruction omitted). Ten excluded; 20 cross-module shape groups covering 45 extents / 2,852 arithmetic sites agree. For example a 2,381-byte shape with 272 arithmetic sites appears across FG-2A, VT-5 and SSL; a 3,075-byte shape with 222 arithmetic sites appears in Trackspacer and MixHead. Matching shapes flag possible common code, not provenance or equivalence. 246 high-arithmetic extents remain after deprioritizing these 45. More duplication may remain, especially different builds or altered operands. Top remaining candidates and exact scope hashes are in the machine-readable summary, not verified audio processor entrypoints.

## Validation

Two owned Windows PE regression methods passed locally with real clang/lld-link and both actual disassemblers: unwind-bound selection, lane deduplication, deterministic selection, exclusion overlap, fingerprint and bounds rejection, plus a shape fixture proving different immediate values can match while different arithmetic mnemonics do not. Exact tested source/test blobs matched. Parent CI 8/8 passed; new CI unverified. Full local 432-window report SHA-256 recorded in JSON. No vendor bytes, constants, listings or reconstructed implementations uploaded. No execution of vendor plugins, protection bypass, audio testing, production DSP or SkellCore changes.
