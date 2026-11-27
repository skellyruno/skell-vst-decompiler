# Matched attack, allpass dispersion and split-filter color research — 2026-11-27

Parent cc66045d3b2937003ff98639ffeb600f740b09e7. Cached offline kit 13/13 verified. Recovered 36 original recordings by matching the earlier measurement fingerprints, including two archive-labeled dry takes; other excerpts already processed and potentially related. Verified exact owned baseline header Git blobs and three new benchmark/adapter blobs. No vendor execution or new vendor static analysis.

## Compressor: matched measured attack and hold sweep
Original ProgramLeveler at 4 ms, -18 dB threshold, 4:1 ratio, 120 ms release, unity makeup, full wet. Existing LevelerPeakHold tested at 0/2/5/8/12/20 ms hold; calibrate candidate attack to approximately 7.83 ms to match first 90%-of-steady-gain-reduction crossing on a .5 step in dB. All six candidates match crossing sample 709/771/1542 at 44.1/48/96k. This matches one step, not the entire envelope. No new engine selected. 21 tone conditions x 7 = 147 renders; 12 burst/recovery conditions x 7 = 84; 36 vocals x 7 = 252. All outputs finite, no over-scale samples for vocals.

At 48k, coherent harmonic-bin distortion at matched t90 (dBc):

| Hz | Original | 0ms | 2ms | 5ms | 8ms | 12ms | 20ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | -62.26 | -60.54 | -60.54 | -60.61 | -60.95 | -62.35 | -75.6 |
| 30 | -69.31 | -67.28 | -67.29 | -67.63 | -69.17 | -76.12 | -121.76 |
| 50 | -78.22 | -75.9 | -75.98 | -78.14 | -91.1 | -125.44 | -125.44 |
| 100 | -90.29 | -87.72 | -88.78 | -130.78 | -130.78 | -130.78 | -130.78 |

Longer hold reduces steady-state ripple, depending on crest interval. At 20Hz, 12ms gives little improvement, 20ms lowers harmonic energy; at 50Hz, 12ms is sufficient for the tested tone. This motivates adaptive hold, not automatic adoption. For 12ms candidate vs original: median raw vocal gain -1.865 vs -2.517 dB; median peak -7.320 vs -7.449 dBFS raw, -7.981 vs -7.449 after independent RMS match. All six hold durations reduce raw peaks on 1/36, matched peaks on 28/36. RMS matching removes average level differences, not all spectral/dynamic differences. 10/50/250/1000ms burst recovery to 10% initial GR at 48k: original 386.02/384.08/434.81/457.31 ms, 12ms candidate 333.42/383.98/434.83/457.31 ms; short bursts have unequal initial GR (6.08 vs 6.856 dB for 10ms), so not identical-state release comparisons. No listening or complete transient equivalence.

## First-order allpass dispersion
Independent ideal fixed first-order allpass model (not a new native engine). H(z)=(a+z^-1)/(1+a*z^-1), a=(1-f)/(1+f); group delay in samples (1-a^2)/(1+a^2+2a*cos(w)). 90 impulse-to-complex-response checks over three rates, five fractions and six frequencies, max absolute error 7.85e-16. Flat magnitude is not constant delay. At 44.1k and f=.5, group delay at 1/4/8/12/16/20k is .502/.532/.640/.872/1.313/1.881 samples; eight traversals accumulate ~11.04 excess samples at 20k relative to ideal half-sample delay. These are fixed linear model values, not modulated delay performance. Further candidate work: higher-order allpass vs bounded FIR and time-transition artifacts.

## Independent split-cutoff saturation
Offline SciPy 4x FIR chain: 161-tap Blackman up/down filters, same total alignment 40 base samples, original-style tanh asymmetric shape and 5Hz DC block; not exact native implementation parity. Four configurations (up/down cutoff in cycles/base sample): .45/.45, .475/.45, .45/.475, .475/.475. 36 coherent tone settings x4 = 144 renders, 36 vocals x4 = 144 renders. Initial tone measurement accidentally included end-of-input filter transient; corrected by adding 128 guard input samples and measuring the interior coherent quarter-second after 1s warmup. Only corrected values recorded. At 44.1k 20004Hz input .5 peak:

| Up/down | Fundamental dBFS | Residual dBc | Absolute residual RMS dBFS |
|---|---:|---:|---:|
| 0.45/0.45 | -9.733 | -77.893 | -90.637 |
| 0.475/0.45 | -6.749 | -54.378 | -64.137 |
| 0.45/0.475 | -4.326 | -83.302 | -90.638 |
| 0.475/0.475 | -1.341 | -59.785 | -64.136 |

Widening downsampling only restores 5.408 dB fundamental here without increasing absolute nonharmonic residual; widening input interpolation increases unwanted energy sharply. Across all 36 settings, down-only widening restores >.01 dB fundamental with <=.1 dB absolute residual worsening in six settings; other settings may trade off. Residual is nonharmonic bins excluding DC and harmonic-coincident aliases; relative residual after fundamental normalization is not a full alias metric. Vocal median high-band fraction (8–16k) essentially unchanged, over-scale excerpts 15/15/14/14, headroom unresolved. Do not promote. Need native asymmetric cutoff candidate, same latency, matched spectral comparisons, peak protection and listening.

## Reproduce and limitations
Run python benchmarks/owned_hold_and_allpass.py --manifest /private/manifest.json --output /private/hold.json and python benchmarks/owned_color_split_cutoff.py --manifest /private/manifest.json --output /private/color.json. GCC and NumPy/SoundFile/SciPy needed. Full runs completed locally, exact adapter/script blobs verified; no fresh hosted full-suite results for new head. Private manifests/audio/per-input rows kept local. Existing vendor backlog (854/90/692) unchanged. No new UI, VST3, production or approved-engine edits. No new presence or pitch experiments this pass; protect Classic/Crystal and all current approved sounds.
