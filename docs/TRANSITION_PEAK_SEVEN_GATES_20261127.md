# Seven-gate DSP research — transition and peak prediction

Parent 001c96f633652bb757a4a6f06a150279198890bb, all eight previous workflows passed. Verified the latest cached Quick4 kit 13/13 and all 36 prior private vocal hashes. Source hashes in adjacent aggregate. No vendor binary replay, no private audio in Git, no approved engine changes.

## Lookahead limiter
New ReconstructionGuard has a 17-sample ring, four reconstruction phases and 16-sample output alignment. For each window and each stereo channel, evaluate signed reconstruction or the absolute sum of weighted inputs. Cap gain for all contributing samples until they leave the ring; use linked downward gain cap and 60ms release. For absolute-sum mode, triangle inequality ensures each declared output reconstruction is <= ceiling (up to arithmetic tolerance) as every sample's nonnegative gain is bounded by ceiling divided by the corresponding window's absolute sum. Does not prove a ceiling for any different reconstruction filter or analog reconstruction. Signed prediction is less conservative but varying gains can invalidate its prediction.

Six-rate optimized and ASan/UBSan tests passed (8/44.1/48/96/192/384k); exact 16-sample low-level delayed path, random signal reconstruction oracle maximum .8839872 vs -1dBFS .8912509. 36 fingerprinted vocals after fully wet split color, aligned output:

| Mode | Max sample dBFS | Max estimated 4x | Max estimated 16x | 16x overload excerpts | Median relative RMS gain |
|---|---:|---:|---:|---:|---:|
| untrimmed | 1.453 | 1.987 | 1.987 | 19/36 | 0.000 |
| fixed_minus3 | -1.547 | -1.013 | -1.013 | 0/36 | -3.000 |
| signed_prediction | -1.000 | -0.899 | -0.676 | 0/36 | -0.206 |
| absolute_bound | -2.144 | -1.505 | -1.483 | 0/36 | -3.877 |

16x Kaiser polyphase estimate is independent of the guard kernel, not certified true peak. Signed candidate promising for level preservation; conservative bound loses more level than fixed trim. Neither approved. No mix/bypass plugin integration or listening test.

## Time-transition second-order delay
TransitionDelay2 has two independent preallocated fixed-coefficient feedback loops with second-order Thiran section, near-integer fractional settings rounded; no coefficient modulation within either active section. On request, warm inactive bank ceil(target samples)+128, then smoothstep 25ms output crossfade. Keep old feedback running until retirement. Warmup costs audible response time and old feedback is retired, not preserved indefinitely. Ring validity avoids clearing memory in process. Six-rate finite/transition stress, exact dry path, and integer old echo continuity during warmup passed. 36 real-vocal renders, .7 feedback, 120->180->90ms + half sample request, append 250ms silence, nonzero tails on all; maximum +3.025dBFS. Not a complete tempo mapping/automation proof or peak-safe engine. No model integration or old-model changes. Continuous rapid requests coalesce; new bank history is not copied.

## Saturation selectivity
Existing 4x native split cutoff kernel; four configurations (span,up/down): 40 450/450, 40 450/475, 80 450/475, 80 465/475. Same 36 tone settings and 36 vocal excerpts, four renders each. Align each engine by its own latency. At 44.1k 20.004kHz .5 peak:
| Span/up/down | Fundamental dBFS | Absolute nonharmonic residual RMS dBFS |
|---|---:|---:|
| 40span450/450 | -9.733 | -90.637 |
| 40span450/475 | -4.326 | -90.638 |
| 80span450/475 | -3.769 | -105.788 |
| 80span465/475 | 0.206 | -63.256 |
80 450/475 improves fundamental >.01dB with <=.1dB residual worsening against 40 450/475 in 4/36 settings. Wider input at 80 loses alias suppression, only 2/36 meet gate. Nonharmonic metric excludes aliases coincident with harmonics. 80 span doubles alignment and is slower in native render; not a default or overall winner. Consider only opt-in quality mode after additional proof and PDC handling.

## Compression and presence
No identified verified real bass/drum stems in checked Library and existing archive files. Do not substitute generated signals or label processed vocal references as real instrument stems. Bass/drum gate remains open. Presence existing private three-take A/B archive revalidated: 15 decoded FLACs, frame/rate equality per group, max RMS delta 2.45e-8 dB, 4x estimated peak <= approximately -1dBFS. Six blind comparisons prepared in self-contained private HTML (reference outside vote); no subjective votes yet, browser interaction not tested. Do not commit media or private rows.

## Playground challenger
Used corresponding archived 292b03f source from approved build, verified normalized key Git blobs and pinned SnapCore SHA. Current Playground PR #19 head 1a32b8f adds comparison gate, no DSP changes. Portable renderer build command: g++ -std=c++17 -O2 -DSKELLY_META_TEST=1 -DSKELLY_PLAYGROUND_RENDER=1 -Idsp -I../snap tools/render.cpp -o renderer. Temporary candidate changed only finalMotionSpeed factors in dsp/PlaygroundBank.hpp from .70/.80 to .85/.90 for TESTTUNE/META; compiled separately and restored source. Use final_challenger_sweep.source_context/render (final=True) on two fingerprinted dry takes, modes 1/2/3/4, speeds 0/10/25/100, common PDC 110, fixed mask 2773, not verified song key. 32 pairs / 64 renders. Classic/Crystal 16/16 exact protected pairs. TESTTUNE six of eight exact; median spectral envelope .6374 -> .6762 dB; coverage .95686 -> .95243. META four of eight exact; median envelope .94907 -> .95091; pitch error worsened in changed 10/25ms cases; aggregate median pitch unchanged. No sample overload. Reject temporary candidate; no repo engine changes. Full fifth engine MetaTune 2.5 unavailable in portable target and not tested.

## Multi-instance native proxy
Owned color -> delay -> signed reconstruction guard. 44.1k, 128 samples, one thread, one dry recording, 64 warmup + 512 measured blocks per count, deliberate delay request at block 256. Budget 2.90249ms.
| Chains | Median ms | p99 ms | Max ms | Misses |
|---:|---:|---:|---:|---:|
| 1 | 0.044387 | 0.117428 | 0.3048 | 0/512 |
| 4 | 0.188935 | 0.364961 | 0.579724 | 0/512 |
| 8 | 0.409407 | 1.082103 | 2.422956 | 0/512 |
| 16 | 0.781819 | 1.87581 | 3.32678 | 2/512 |
16 chains miss two deadlines; do not call this DAW profiling. No actual VST3 host, pluginval or Windows/FL Studio run for candidates.

## Reproduction
Run native test with GCC C++17 O3 and ASan/UBSan (CI registered). Python benchmarks/owned_transition_peak.py --manifest /private/manifest.json --output /private/batch.json --start 0 --count 9 --tones; remaining batches --start 9/18/27 without --tones. Compile benchmarks/owned_multi_instance.cpp -std=c++17 -O3 -Wall -Wextra -Werror; run on an authorized interleaved stereo float64 native-endian raw file with sample rate argument. Local timings are not paired host CPU. Private source and results stay local. Static vendor backlog 854/90/692 unchanged; no production integration, approved default edits or new UI. Latest hosted CI pending.
