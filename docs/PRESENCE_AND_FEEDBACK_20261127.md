# Presence topology and recursive delay evidence — 2026-11-27

Parent 3cb4e032ac079221c08e94af744a174baccecc10. All eight parent decompiler workflows passed. Cached Quick4 kit manifest 13/13 passed. Recovered all 36 actual vocal excerpts by exact earlier source file SHA-256 fingerprints, 2 archive-labeled dry and 34 processed excerpts, original 44.1 kHz. No private files, identities or per-input metrics in Git.

## Independent presence topology

The previous conversation's interrupted complementary-presence experiment had not been committed. Rebuilt the exact prior original PresenceEngine header (Git blob b81bc2c...), complementary candidate and local native fixtures; verified source blobs. The existing LR4 low+high sum has unity steady-state magnitude at neutral but all-pass phase; at the crossover the wet output is opposite to the original dry. At 48 kHz/2600 Hz/neutral 50% wet the measured numerical null was -243.015 dB, versus exact zero gain for the complementary candidate. With +3 dB boost, amount zero and 50% mix, gain -19.732 versus +.890 dB. A deep null is not broadband attenuation and the exact residual is floating-point dependent.

New independent PresenceComplementary retains the high-band LR4 detector and smooth gain law, but adds (wet*(gain-1))*complementary first-order TPT highpass to dry. No added transport delay, no change to original class. This changes active filter shape and is an alternative, not a drop-in sound-equivalent replacement.

108 paired tone cases, three rates; 54 neutral candidate cases exact. 144 paired real-vocal cases, four conditions; 72 neutral candidate cases exact. At neutral 50% wet, old median RMS -1.336 dB, worst -2.341 dB; candidate exact. Added RMS-matched Welch spectral-band comparison. Median 1–4k neutral half-mix loss -3.873 dB old, 0 candidate. Active 50% wet medians:

| Band | Original | Complementary |
|---|---:|---:|
| 80–250 | +1.194 | -.196 |
| 250–1000 | +.743 | -.116 |
| 1000–4000 | -3.719 | +.256 |
| 4000–8000 | +.022 | +.830 |
| 8000–16000 | +1.832 | +.978 |

At full-wet active, sample peaks +2.075 -> -.461 dBFS, over-scale excerpts 2 -> 0. Median raw RMS gain +.249 -> +.434 dB. Active high-band response differs, so no promotion based solely on headroom. RMS matching is not a listening test. Native GCC optimized and ASan/UBSan tests passed at six sample rates, five wet positions, exact neutral/dry, stereo swap, reset/nonfinite input. Added CI owned-only C++ regression. No full local suite or new hosted CI claim. Reproduce locally with python benchmarks/owned_presence_phase.py --manifest /private/manifest.json --output /private/metrics.json. Full private report digest in JSON.

## Skellay: recursive decay and stereo feedback

[Skellay 6271e2fc7136c4144d2254e83af4d51e270f51b1](https://github.com/skellyruno/skellay/commit/6271e2fc7136c4144d2254e83af4d51e270f51b1) integrates optional prepare-time wet trim and records native evidence. Previous interpolation commit 0c60368 Windows CI passed. At .75 feedback, half-sample linear loop adds abs(cos(pi*f/fs)) decay to each repeat. Cubic readout preserves more initial high band but does not change the original linear loop. 45 analytical decay comparisons at three rates and 72 stereo difference impulse observations passed. At 44.1k and 12k the per-repeat loss is -6.156 dB vs -2.499 integer. 108 isolated real-vocal echo renders: median 8–12 kHz per-repeat loss -2.499 integer, -4.452 fractional linear, -4.476 fractional cubic read. Crossfeed side gain .75/.375/0/-.75 at cross 0/.25/.5/1; width and crossfeed should be separated in future design.

288 paired wet-trim cases, 576 full-input renders: -3 dB optional wet trim after feedback write, max sample peak +.653 -> -2.347 dBFS, four over-scale untrimmed conditions, zero trimmed. Maximum oracle error 5.96e-8. Six rates, two interpolation modes, 100k frames each with changing time/feedback/cross and resets, optimized + sanitizer passed. Zero trim default retains original expression; original three production models untouched. New native research delay not exposed in plugin selector/state/GUI. [Detailed report](https://github.com/skellyruno/skellay/blob/6271e2fc7136c4144d2254e83af4d51e270f51b1/docs/RESEARCH_DELAY_FEEDBACK.md).

## Limitations and next gates

New CI pending; prior static backlog unchanged (854 unknown destinations, 90 conflicts, 692 value-flow candidates). No new vendor algorithm evidence, production transfer, CPU benchmark, certified true peak, FL Studio validation or new UI captures. Next research: independent unity-magnitude fractional feedback option with modulation-safe state transitions; separately parameterized stereo loop width; complementary presence listening and consonant/low-mid fidelity checks before Core integration. Protected Classic/Crystal, Chorus/Flang and current production defaults unchanged.
