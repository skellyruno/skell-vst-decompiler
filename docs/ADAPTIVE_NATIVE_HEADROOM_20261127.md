# Adaptive crest hold, second-order allpass and native split-filter headroom

Parent 5311bb096c7b7c1d256b592d3929ec84d3d9555e. All 36 previous private vocal source hashes rechecked; two archive-labeled dry, 34 processed. Latest Quick4 kit manifest 13/13. Exact original header blobs and new tested source blobs in adjacent report. Existing approved engines, presets, UI and vendor evidence untouched.

## Adaptive compressor
AdaptiveHold is a separate experimental full-wet, fixed-threshold/ratio comparator. Estimate crest interval from linked channel magnitude local maxima above -18 dB, with relative peak gate; set hold to 1.15 times interval, bounded 2–32 ms; expire after no qualifying crest. It is not a pitch detector and can misread polyphonic or transient material. Preserve original program-dependent release and immediate downward gain. Calibrate all candidate attacks to original 4ms t90 (approx 7.83ms) on .5 step at 44.1/48/96k, within one sample. Six-rate optimized/sanitized regression checks hold estimates for 20/50/200Hz, finite/reset, stereo swap, bounded gain. 72 steady-tone renders, 48 burst renders, 144 native real-vocal renders.

| Hz at 48k | Original | Fixed 12ms | Fixed 20ms | Adaptive |
|---:|---:|---:|---:|---:|
| 20 | -62.256 | -62.348 | -75.595 | -119.265 |
| 30 | -69.312 | -76.122 | -121.764 | -121.764 |
| 50 | -78.223 | -125.438 | -125.438 | -125.438 |
| 100 | -90.292 | -130.78 | -130.78 | -130.78 |
| 200 | -102.31 | -136.451 | -136.451 | -136.451 |
| 1000 | -129.849 | -148.865 | -148.865 | -148.865 |

Harmonic-bin energy, dBc, not perceptual quality. Adaptive 20Hz -119.265 vs -62.256 dBc. Only one of 36 raw peaks reduced, 28/36 RMS-matched peaks reduced; median gain original -2.517 vs adaptive -1.863 dB. Adaptive burst recovery at 48k 333.27/383.92/434.81/457.31ms for 10/50/250/1000ms burst vs original 386.02/384.08/434.81/457.31; brief burst initial gain reductions differ. No bass/drum recordings or listening approval. Do not replace original.

## Higher-order fractional delay
Second-order fixed Thiran section with D=1+f, f=.05–.95. Coefficients a=-2(D-2)/(D+1), b=(D-2)(D-1)/((D+1)(D+2)); numerator reversed denominator. Native impulse versus analytic complex response, 90 checks, maximum 9.93e-16. Energy unity, DC gain unity and DC group-delay moment validated. Compare first order plus integer with same total delay. 81/90 closer to ideal group delay, but at 44.1k f=.5, 20k group delay grows from 2.881 to 3.281 samples (target 1.5), while at 8k improves 1.640 -> 1.538. No recursive feedback integration, time-varying coefficients, or tempo transition test. Keep separate from Skellay models.

## Native asymmetric oversampling
ColorSplitNative independently widens output FIR only (450/475), or input only (475/450); original 450/450 remains unchanged. Same 161 taps at 4x, 40 sample alignment. Equal cutoffs native exact at 36 tone and 36 vocal configurations, six-rate regression max difference zero; exact dry latency. 144 native tone and 144 native vocal color renders (include equal-cutoff parity). 44.1k 20.004kHz .5 peak: fundamental -9.733 -> -4.326 dBFS with output-only widening, absolute nonharmonic residual -90.637 -> -90.638 dBFS; input widening residual -64.137. Only 6/36 conditions satisfy >.01dB fundamental restoration and <=.1dB worsening absolute residual. Not an overall winner, and nonharmonic bins omit coincident aliases.

## Headroom
36 fully wet output-only split renders: 14 sample overloads, 18 estimated intersample overloads (4x polyphase). LinkedSampleGuard caps sample magnitudes at -1dBFS with instantaneous downward and 60ms exponential recovery, no explicit lookahead. Zero sample overload but eight estimated intersample overloads, max +.966dBFS. Fixed -3dB trim: zero sample/estimated overload, worst 4x estimate -1.007dBFS. Not a true-peak limiter. No production promotion; guard is after fully wet color, not partial wet or bypass. Fixed trim is preferable on this corpus if transparent headroom is desired; no universal ceiling.

Full expanded headroom/timing attempt timed out after 24 inputs without output; not counted. Completed separately selected 6 (two dry, four processed), three alternating repeats, 72 timed native calls. 16x Kaiser interpolation max estimates untrimmed +1.987, fixed -3 -1.013, sample guard +.369, guard plus -2.5 -2.131 dBFS. Median paired timing change adaptive +2.73% slower, split -1.39% faster; small sample, wall-time includes prepare/adapter, no claim of host CPU improvement. Estimated intersample peaks not certified true peak. Full 16x and DAW profiling pending.

## Verification and reproduction
Optimized and ASan/UBSan native test passed at 8/44.1/48/96/192/384k, exact equal-cutoff and dry path locally. Registered native regression in existing CI. Run `python benchmarks/owned_adaptive_native.py --manifest /private/manifest.json --output /private/metrics.json` and `python benchmarks/owned_headroom_timing.py --manifest /private/six-input-manifest.json --output /private/timing.json`. Use GCC, NumPy, SciPy, SoundFile. Full benchmark and bounded timing subset completed; only aggregate values committed, no private inputs or individual rows. No new vendor corpus replay (854/90/692 unchanged). Presence listening and new pitch Playground challenger not completed this batch; retain Classic/Crystal and approved defaults. No new Windows plugin build/UI/host or listening approval. New CI pending.
