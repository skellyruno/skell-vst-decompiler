# Compressor attack calibration and complex delay response — 2026-11-27

Parent 805cd80bbe1d7408d29a4e9780815f5822cbe32e. Reconciled with the concurrently completed complementary-presence and recursive-delay milestone, preserving all its findings and code. Cached Quick4 checksums 13/13 verified. Recovered all 36 real vocal excerpts by exact prior source file SHA-256, verified frames and rates. Same 159.25s private corpus (2 dry, 34 processed); not independent performances necessarily. Original IndependentEngines.h Git blob verified before compiling. No vendor binaries executed or reconstructed.

## Independent leveler candidate

Original ProgramLeveler has attack smoothing on the peak envelope and a second pole on falling gain. LevelerSingleAttack uses the same detector and activity/release state but follows falling target gain immediately; rising gain uses the existing gain-release pole. No original engine changes. Six-rate optimized and ASan/UBSan tests passed exact dry/unity-ratio behavior, stereo swap, reset, finite handling, monotonic step and steady analytic gain. No production selection.

12 step conditions (3 rates x 4 nominal attacks), amplitude .5, threshold -18 dB, ratio 4, release 120ms, unity makeup, full wet. t90 is first sample reaching 90 percent of final gain reduction **in dB**, not a time constant or an advertised manufacturer timing convention. At 48 kHz:

| Nominal attack | Original t90 ms | Single-stage t90 ms |
|---:|---:|---:|
| 1 | 4.021 | 2.063 |
| 4 | 16.063 | 8.208 |
| 10 | 40.167 | 20.500 |
| 30 | 120.500 | 61.479 |

At 4 ms elapsed for nominal 4 ms: original 1.798 dB, single-stage 5.997 dB. Both converge to the same ~8.985 dB static gain reduction. A control time constant is not a measured t90; calibrate the intended meaning rather than calling the legacy control defective by convention alone.

## Equal-measured-response calibration

Binary search candidate attack in [4,12] ms to match original 4 ms t90 on the .5 step. Exact crossing sample at all three test rates: 709/771/1542; candidate attack 7.83424/7.82802/7.83311 ms. This only matches one step condition, not the entire dynamic law.

At 48 kHz, steady coherent sine harmonic-bin energy relative to fundamental:

| Frequency | Original 4 ms | Single 4 ms | Single matched t90 |
|---:|---:|---:|---:|
| 50 | -78.22 | -75.62 | -75.90 |
| 100 | -90.29 | -87.43 | -87.72 |
| 200 | -102.31 | -99.30 | -99.60 |
| 1000 | -129.85 | -126.72 | -126.73 |

These are in-band harmonic estimates, not a full alias or perceptual distortion metric. The single-stage candidate retains slightly more harmonic distortion even at matched t90.

Release: high step .5 for 10/50/250/1000 ms, then .025 for 2 seconds, measure first crossing of 10% of each case's initial reduction in dB. At 48 kHz, original recovery 386.02/384.08/434.81/457.31 ms, single-stage nominal 350.13/384.08/434.81/457.31, matched 333.27/383.92/434.81/457.31. For the 10ms burst initial GR differs (6.080/8.427/6.856 dB), so do not treat these relative recovery times as identical-state comparisons. Sustained bursts demonstrate existing activity-dependent recovery retained. No claim of optical model equivalence.

## Real-vocal evidence

144 paired cases / 288 renders: 108 same-nominal (1/4/10 ms) and 36 matched-t90 (original 4ms, candidate 7.83424ms at 44.1k). All finite, no over-scale samples. RMS matched differences calculated separately; raw peak results remain unnormalized.

| Case | Candidate lower peak count | Original median raw gain dB | Candidate median raw gain dB | Median RMS-matched difference dB |
|---|---:|---:|---:|---:|
| 1 ms nominal | 30/36 | -3.964 | -4.035 | -37.35 |
| 4 ms nominal | 28/36 | -2.517 | -2.609 | -35.51 |
| 10 ms nominal | 25/36 | -1.464 | -1.567 | -34.30 |
| Matched t90 | 1/36 | -2.517 | -1.862 | -31.60 |

The apparent peak advantage at equal knob settings largely disappears when step response is matched. Original is smoother on the tested coherent tones and reduces more vocal RMS at equal t90. Preserve the approved/default algorithm; use candidate only as a separate transient-control experiment. No listening preference, true-peak, real-time CPU or host claim. Run `python benchmarks/owned_leveler_attack.py --manifest /private/manifest.json --output /private/metrics.json` with NumPy, SoundFile, GCC. Private manifests/rows/audio remain local.

## Delay: expanded complex oracle

[Skellay 5ee9a58](https://github.com/skellyruno/skellay/commit/5ee9a58fffb3a790ee62f2d85a1cfb62424ddcf4) adds 9,216 complex mid/side echo-spectrum comparisons across 96 fixed control combinations, 8 echoes, six frequencies, three rates. Retested exact latest wet-trim header after branch advanced; optimized and ASan/UBSan passed, max absolute complex error 1.21e-7. At 44.1k, 12k tone bin, half-sample, .9 feedback: linear mid echo 1/4/8 = -3.66/-17.38/-35.67 dB; cubic output = -1.48/-15.20/-33.49 dB. Cubic output improves one pass only; same recursive linear feedback. .35 crossfeed reduces relative side/mid by ~10.46 dB each recurrence. Absolute complex tolerance is not relative dB precision near cancellation. Existing modes and new experimental wet-trim settings preserved. No new delay integration.

## Verification

Exact tested source blobs matched. New native optimized/sanitizer regression registered in CI, latest hosted validation unverified. Existing prior vendor unresolved counts unchanged (854 destinations, 90 boundaries, 692 local candidates); no new vendor static analysis in this batch. No GUI or approved engine changes, so no new production VST3 or screenshot claimed.
