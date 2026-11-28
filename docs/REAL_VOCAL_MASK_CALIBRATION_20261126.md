# Real-vocal calibration and bounded mask replay — 2026-11-26

Parent 65805e839da2a1b357ad2b8ebc616722d83904d5. All eight parent CI workflows completed successfully. Cached Quick4 manifest verified 13/13. No native plugin UI change, vendor execution, protection analysis or production DSP change.

## Private input intake

Used 36 non-duplicate excerpts of actual vocal recordings, 159.2501 seconds total at original 44.1 kHz. Two explicitly archive-labeled dry clips, one already-processed module input, 18 processed main/full reference excerpts and 15 processed adlib excerpts. Verified 33 archived original playback SHA-256 and frame counts; excluded three historical different-take entries. Kept stages separate, no source/target matching claims. Excerpts can overlap the same performances. Private manifests, audio files, titles, individual results and audio fingerprints remain outside Git.

## Existing bounded vendor-mask replay

Replayed the original 8 fingerprints and 479 recorded scope hashes with raw GNU/LLVM maps and the union of prior local and cross-window guards. New previously owned-calibrated mask detector reports 1,781 selected bitwise-register operations, 37 comparison masks, five narrow complementary selection observations across four Panagement windows; no complementary selections in the other seven targets. Zero is not proof of absent conditional processing. No new target windows decoded, no runtime destinations inferred. All 854 unknown destinations, 90 boundary conflicts and 692 prior value-flow candidates unchanged. Full local scope report SHA-256 e9fc5e2c54654c4072faad596fb7a2a67993b0df318119d84d4035aa32552a8b.

## Native real-vocal audio benchmark

New generic private manifest-driven harness compiles the two existing owned adapters with GCC -O2 -Wall -Wextra -Werror. All 36 excerpts run through nine configurations, fully wet, existing default presence/leveler parameters, saturation +12 dB drive/.12 asymmetry/output 0 dB. 324 wet configurations, three timed repeats each (972), 324 exact delay-aligned dry identity checks, 180 exact block-partition comparisons for the five original engines. All outputs finite. Alignment uses previously measured dry delay 0/40/80 samples and zero-padding to retain the input duration, not full tail analysis. RMS matched spectral and difference metrics computed separately from raw peaks; fourfold SciPy interpolation is an estimated peak, not a certified true-peak meter.

| Configuration | Median raw gain dB | Raw sample-overload excerpts | Estimated peak over 0 dBFS excerpts | Worst estimated peak dBFS | Median ms/audio-second |
|---|---:|---:|---:|---:|---:|
| presence | 0.25 | 2 | 2 | 2.32 | 1.33 |
| leveler | -2.52 | 0 | 0 | -2.44 | 0.96 |
| color_1x | 10.85 | 5 | 22 | 3.44 | 1.18 |
| color_2x | 10.85 | 15 | 19 | 2.25 | 9.29 |
| color_4x | 10.85 | 15 | 19 | 2.12 | 18.38 |
| color_2x_wide40 | 10.85 | 14 | 19 | 2.11 | 9.25 |
| color_4x_wide40 | 10.85 | 14 | 19 | 2.01 | 18.22 |
| color_2x_wide80 | 10.85 | 14 | 20 | 2.17 | 15.66 |
| color_4x_wide80 | 10.85 | 14 | 20 | 2.08 | 30.76 |

None of the original inputs has estimated peaks over full scale. Saturation adds approximately 10.85 dB median raw RMS; its float output can exceed full scale, not necessarily hard-clipped internally. Presence also has two over-scale excerpts. Leveler had none. The 2x default is close to default 4x on these vocals (median RMS-matched difference -91.40 dB) and roughly half the observed wall time; this is not an alias or universal quality comparison. Wider cutoff changes high band level, not proof of perceptual improvement. Timing includes setup/adapter and uncontrolled container load, not host CPU.

## Headroom experiment

New isolated native adapter tests existing color output control at -12 dB, fully wet. A full 36-input run timed out before producing a report, and no partial results counted. Completed separate three-input subset (two dry, one processed module input), all seven color configurations: 21 comparisons. Maximum measured waveform scaling error exactly zero against baseline times expected gain; highest estimated peak +2.7368 to -9.2632 dBFS; no output samples above full scale. A fixed trim is not a limiter, AGC or universal headroom guarantee. Defaults unchanged. Presence gain staging remains open.

## Reproduction and privacy

Run `python benchmarks/owned_private_vocal.py --manifest /private/manifest.json --output /private/metrics.json` with explicitly selected owned local files. Manifest input rows need id, stage, path and SHA-256; optional listening directory and IDs create 24-bit FLACs with common per-group headroom. Three private listening groups verified, 30 files at same lengths/rates per group, RMS matching maximum absolute 2.13e-8 dB, max estimated peak approximately -1 dBFS. No subjective preferences claimed. Run `python benchmarks/owned_private_headroom.py --manifest /private/subset.json --output /private/headroom.json` for trim check. Requires NumPy, SciPy, SoundFile and GCC. No private recording or individual result belongs in this repository. Three new analytical tests and 25 prior local methods passed (28 total). Exact new source blobs recorded; current CI pending. Public summary contains aggregate metrics only, not source identities. No vendor equivalence or release validation.
