# VMR paired processor dispatch navigation — 2026-11-24

Continuation of the 128-region atlas and the exact-build class plans; all prior reports retained. Reconstructed the privately supplied four-part archive; SHA-256 353f23373ac05d7b2121c313073f08c708e879d839115d4ce5d30657732f481e. All three selected module fingerprints match class_navigation_summary.json.

Six selected methods decoded. Across all three modules the long and short wrappers have 537/341 bytes, 117/81 decoded instructions respectively. Both paths use 32-frame chunking and handle a remainder; the longer wrapper reads two buffer pointers, the shorter one. This is evidence of differing buffer handling, not proof of host mono/stereo selection. Six executable pointer candidates sampled per table; the fourth and fifth zero-based indices point to the same target within each table.

| Module | Wrapper | Selector displacement | Table | Slot 4/5 target | Target unwind bytes | Instructions | Existing overlapping atlas records |
|---|---|---|---|---|---:|---:|---:|
| FG-116 | 0x160540 | 0xd0 | 0xfef548 | 0x1619a0 | 2680 | 607 | 3 |
| FG-116 | 0x160910 | 0xd0 | 0xfef518 | 0x162420 | 2604 | 571 | 0 |
| FG-2A | 0x1561c0 | 0x190 | 0x1008518 | 0x156b20 | 1243 | 239 | 3 |
| FG-2A | 0x156590 | 0x190 | 0x10084e8 | 0x157000 | 953 | 193 | 0 |
| FG-Stress | 0x160a30 | 0x360 | 0x1014588 | 0x162790 | 4390 | 851 | 6 |
| FG-Stress | 0x160e00 | 0x360 | 0x1014558 | 0x1638c0 | 4041 | 788 | 0 |

The three longer paths overlap previously studied evidence; the three shorter paths have no overlap with the current atlas, totaling 1552 decoded instructions. This is new navigation evidence, not new verified gain laws. Static call counts long/short: 24/24 FG-116, 14/14 FG-2A, 39/38 FG-Stress. Indirect-call counts: 0/0, 0/0, 15/15. Runtime selector values, table extent, and downstream dynamic targets remain unknown.

Reproduce with python -m skell_vst_decompiler.variant_navigation /private/modules reports > /tmp/vmr_variant_navigation.json. Write to a temporary file outside reports first to avoid an empty JSON input created by shell redirection. Only private authorized originals; no binaries, vendor code or calibration arrays committed. The exact-build run reproduced byte-for-byte. Initial verifier incorrectly assumed a common selector displacement; corrected to module-specific fields. Local prior Multi-Engine Lab archive suite plus two new tests: 70/70; separate earlier evidence_audit commit CI passed. Current combined CI must be checked on exact new head. No runtime host/audio tests or vendor Ghidra execution. TVB hashes confirmed; selected AirExciter, Chorus, PitchCorrector and Demon entry unwind records are short fragments and not complete function extents. No new TVB equations established. Next prioritize uncovered short-wrapper target comparisons; retain all earlier evidence.
