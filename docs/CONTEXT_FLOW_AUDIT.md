# Exact decoder alias and enclosing context audit

Previous 3c831d1b87e99b32f3791328b99c8c07075b489c: 154 tests and all eight CI workflows passed. Six original file hashes checked, including the VMR archive before extracting its three compressor modules. Exact atlas Git blob bc75dc2ee0781189b539897bcb435c7a3f8091bc. Original local static flow comparator blob 0be48199ac808c168045286b2905b58398a91f8c reproduced. GNU 2.44 and LLVM 17.0.0; all 128 prior DSP scopes on four originals redecoded. Evo and the VMR rack were fingerprint-checked only in this batch.

## Alias correction
Exact known WAIT + FNCLEX/FNINIT split/fused equivalence with source-byte checks, no extra interior start. Both original and normalized counts retained. Four FG-2A aliases observed, one scope gained flow coverage: reached spans 1890 -> 1901 (normalization changes the denominator 2846 -> 2854), reached bytes 9733 -> 9765 (+32). Other tracks unchanged. This is a small analyzer correction, not additional recovered DSP code.

## Enclosing context experiment
Unique x64 unwind containment for 112/128 scopes across 34 records. Compare exact child-span matches from the narrow scope, then wider record with the same child seed, then wider record with its own start as seed. All 112 child starts and record starts agreed between decoders, and all agreed child spans matched the wider decode. No assumed function extents. Exclude 16 scopes without unique full containment.

| Track | Contained scopes | Narrow reached | Wider, same seed | Wider, record-start seed |
|---|---:|---:|---:|---:|
| TVB | 58 | 3840 | 3842 | 3842 |
| FG-116 | 7 | 982 | 982 | 982 |
| FG-2A | 41 | 1575 | 1575 | 980 |
| FG-Stress | 6 | 1001 | 1001 | 1001 |

FG-2A's earlier 956 not-reached spans decompose into 207 observations in contained scopes and 749 in excluded scopes; the exclusions are a coverage limit, not a finding of inaccessible code. Widening the contained scopes with the same seeds adds no FG-2A spans. Changing the seed to the recorded extent start fails to confirm 595 locally reached spans across 17 scopes (3546 bytes, summed including overlaps). Exact WAIT alias normalization in the enclosing comparison does not change these totals. This weakens the claim that local snippets establish one confirmed processing path. Alternative entries, unmodeled transfers, exceptional paths and unsupported forms remain possible. TVB gains two matching spans (12 bytes) on widening one scope. Other tracks reproduce local reachability counts from enclosing starts. No runtime or proprietary algorithm identity claim.

Nine focused local unit tests passed. Four real, owned x86/x64 PE assembly fixture cases passed after fixing x86 assembly SafeSEH compatibility metadata; the fixtures are never loaded. Fixture checks confirm branch re-entry and WAIT alias normalization. Tested code/test blob IDs recorded. Existing code and reports preserved, new workflow step added. No private binaries, vendor instructions, or reconstructed proprietary implementation committed. No production plugin changes. Latest CI pending.
