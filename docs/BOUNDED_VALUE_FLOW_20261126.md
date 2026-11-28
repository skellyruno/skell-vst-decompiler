# Bounded local value-flow evidence — 2026-11-26

Parent: e4becb4dcbd7302b095519c90d694985791f5a01. All eight exact reference fingerprints and all 479 previously recorded scope hashes verified before analysis (432 expanded, 47 earlier, 659226 total scoped bytes).

New original scanner tracks selected contiguous legacy SSE register and memory forms with byte-backed operands agreed by both decoders. Per-origin age, precision, arithmetic depth, multiple source expressions, pointer-change and unsupported-instruction barriers, and post-store invalidation. Corrected an LLVM scalar move annotation false negative. It does not infer runtime address identity, audio reachability, numerical dependence, control-flow completeness, or vendor algorithms.

| Module | Expanded regions | Earlier regions | Expanded candidates (16) | Earlier candidates (16) |
|---|---:|---:|---:|---:|
| StandardCLIP |36|5|27|8|
| Trackspacer |36|6|26|34|
| FG-2A |36|8|153|80|
| Panagement |72|5|99|0|
| DeeDoubler |36|7|85|4|
| VT-5 |72|6|90|0|
| SSL Fusion Stereo Image |72|4|64|0|
| MixHead |72|6|51|0|
| Total |432|47|595|126|

At limit 16: 721 counted stores with candidate transformed origins in 83 regions. 394 same-expression and 327 different-expression candidates; expressions may alias, and operations can cancel numerical dependence. 12 expanded candidates in previously shared-shape-flagged regions, 583 in remaining expanded regions. Maximum selected arithmetic depth 7. At limits 3/8/16/32 totals 502/677/721/756 respectively; monotonicity asserted for each region. These counts are not unique DSP functions or reconstruction percentages.

Six targeted local tests passed, including two new methods on owned fixtures; exact tested blobs matched. Previous CI last observed 7 successes and Python in progress. Full new-head CI not yet verified. No vendor binary, source, raw constants, private audio, production DSP, license or UI changes.

Local report SHA-256 e88e351a7bfe60b51423eb51f699ea5ec4053d71577a2bff07d3682313bf41ca (Skell_Bounded_Value_Flow_20261126.json). Input report SHA-256: memory effects 584dfe8493de8793fbacb0df01e4067dcda979bda5290ca039366d9497427e32; eight-target RIP 7fc2fa580d2b86d76a3bc2f3676c8521a01bed9a75f29c05568c7a94ee60824f.
