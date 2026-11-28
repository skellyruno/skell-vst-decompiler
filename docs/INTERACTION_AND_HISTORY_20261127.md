# Replicated control interactions and state history — 2026-11-27

Parent `13c07236bb8303b44939327a2bbc94eed310cb21`; 7/8 hosted workflows passed at audit, remaining static/Windows-host workflow still running. Reused the offline Quick4 kit, all 13 checksums passed. No UI or native plugin changes in this Python research batch.

New original `interaction_analysis.py` implements a two-by-two factorial waveform interaction gate, withholding the joint setting from a three-setting additive predictor. It requires two repeats at every setting, uses explicit noise and resolution floors, and distinguishes unstable, resolved interaction and unresolved interaction. A separate identical-input-suffix test measures observed history persistence in 20 ms windows, including right-censoring. This is not an internal release-constant estimator. `factorial_files` verifies eight distinct capture folders, source/render hashes, unchanged capture metadata, common declared host/module/version/latency/stage, repeat readbacks and exactly two independent public-control axes. It does not authenticate the host or execute vendor code. Timing-changing controls require separate tests. Nine local unittest methods passed, including file tampering, confounding, unstable repeats, silent output, invalid alignment and history censoring.

Independent Pedalboard 0.9.23 built-in processors, 48 kHz, 128-frame buffers, fresh processor per render. Nine distinct control-pair configurations, 4 source cases (synthetic stepped tone, independent noise, two archived recorded-vocal mixes), 4 settings and 2 repeats: 288 renders. Three history sources per configuration, 2 prefixes and 2 repeats: 108 renders. Total 396. All 36 factorial observations showed interaction; repeat RMS error zero on all factorial cells. All 27 history observations resolved persistence. Delay/reverb 6/27 observations still active at 1500 ms (right-censored); all other histories last detected at 20–280 ms on tested conditions. These are independent fixtures, not commercial reference behavior. Two recorded inputs are archived processed vocal mixes, not established independent performances. Source archive SHA-256 045ccc297e53351f9f20033026394d07d02587dd635180cda276e18131b5b7d9; source WAV fingerprints recorded by benchmark. No private samples in Git.

| Processor / control pair | Additive relative waveform error on recorded mixes A/B (%) | Last detected history on A/B (ms) |
|---|---:|---:|
| Compressor threshold / ratio | 14.903 / 14.524 | 40 / 40 |
| Compressor attack / release | 47.685 / 51.115 | 220 / 220 |
| NoiseGate threshold / ratio | 0.804 / 0.644 | 20 / 20 |
| Delay feedback / mix | 45.071 / 44.339 | >=1500 / >=1500 |
| Reverb room size / damping | 14.194 / 20.194 | >=1500 / >=1500 |
| Chorus rate / depth | 100.090 / 104.130 | 80 / 80 |
| Limiter threshold / release | 46.836 / 42.155 | 40 / 40 |
| PeakFilter cutoff / gain | 77.480 / 69.708 | 20 / 20 |
| HighShelfFilter cutoff / gain | 57.553 / 64.979 | 20 / 20 |

Reproduce `PYTHONPATH=. python benchmarks/benchmark_interactions.py PRIVATE_ARCHIVE.zip LOCAL_REPORT.json`. The additive residual is not bounded by 100%, a perceptual score, or proof of nonlinear implementation. Tests use caller-declared metadata fixtures; no vendor captures, source recovery or production adoption. Native IR deadline misses remain unaddressed. All 47 prior planning tiers unchanged; 0/47 verified at 80% gate. Next: licensed public-control captures covering multi-parameter interactions, longer tails, distinct recordings and sample rates, then compare independent models against withheld settings and performances. Maintain full signal-flow evidence separately.
