# Quiet-window peak guard, wet budget, symmetric convolution and listening playback — 2026-11-27

Parent e025d77c05e3a403b6c84eabef1f65fb98231f8e. Reverified prior 36 vocal files and 3 music files, 9 ten-second excerpts (90 seconds); prior source cohort, not new independent performances. Latest identified Quick4 kit 13/13 checksums; isolated pinned Debian development overlay verified, no system package changes. No vendor binary replay, private source publication, or approved engine changes.

## Quiet-window bound and release policy

Let H be maximum L1 norm of declared four-phase reconstruction kernels; when every absolute input sample in the current stereo window is <= ceiling/(H*(1+1e-12)), all weighted absolute sums are <= ceiling with a floating-point margin. The old polarity guard's per-direction lobe bounds then already yield unity, so skip its expensive prefix and residual calculations, but keep all existing per-sample cap minima and gain release state. No change to 16 sample latency, kernel or release law. ReleaseSelectedGuard selects quiet polarity at <=10ms and old release-prefix at longer fixed release, **at prepare only**, not live parameter automation. The 10ms threshold is a research choice, not an optimized musical control.

Optimized and ASan/UBSan six-rate regression passed 864,000 exact channel comparisons (quiet vs polarity and selection vs corresponding reference), including resets and quiet/hot transitions. Real audio 45 excerpts x 3 releases, two exact comparisons per excerpt/setting (270 pairs). No newly claimed true-peak guarantee. The optimized algorithm preserves prior finite-kernel guarantee by exact parity; not certified true peak.

| Corpus | Prior median ms/audio-second | Quiet median | Median paired reduction |
|---|---:|---:|---:|
| Vocals | 9.534 | 4.060 | 56.30% |
| Music | 10.353 | 7.575 | 29.03% |

Timing at 1ms release, three alternating pairs, setup/adapter included, concurrently batched. Median skipped-window fractions .6273/.3658. Not host CPU. At 1/10/60ms, median paired RMS advantage of polarity over prefix .629/.096/.020 dB vocals, 1.375/.170/.032 dB music.

## Release distortion diagnostics

60 controlled 48k configurations (5 sine frequencies 20/50/100/1000/4000 Hz, peak 1.5/3, 6 release settings 1/5/10/20/60/1000ms), 120 renders. Analyze second one-second coherent window of input (guard alignment compensated); harmonic-bin power relative to fundamental, not complete alias or distortion metric; 1000ms may not fully settle. At 50Hz/peak1.5:
| Release ms | Prefix dBc | Polarity dBc |
|---:|---:|---:|
| 1 | -12.144 | -12.679 |
| 5 | -15.682 | -16.722 |
| 10 | -18.864 | -19.417 |
| 20 | -22.521 | -22.816 |
| 60 | -29.399 | -29.506 |
| 1000 | -51.234 | -51.242 |
Fast gain recovery can create strong bass harmonic distortion. Six of 60 conditions worsen >.1dB with polarity, including high-amplitude 1ms conditions. Preserve candidates, do not choose release solely by RMS advantage. Need musical listening and frequency-adaptive release research.

## Wet path gain budgeting

Keep four-bank scheduling and recursive histories intact. Sum active and outgoing banks into primary, retired banks into tail. For primary peak over ceiling, reduce linked primary gain immediately, recover at 30ms. For already bounded primary p and signed tail t, solve |p+g*t|<=ceiling for each channel; positive t cap (ceiling-p)/t, negative t cap (-ceiling-p)/t, zero t cap 1; take min across stereo and use immediate-down/release-up cap. Budget only at output, not inside feedback. Exact dry identity, same target and forced retirement counts versus original in six-rate stress, sample ceiling .891250938133746; fully wet only, no intersample or partial-wet guarantee. Can reduce old-tail audibility and distort dynamics.

45 paired real-audio delay comparisons, .7 feedback, 250ms request cycle, 250ms appended silence. Compare four variants: original raw, budget alone, original plus 60ms prefix guard, budget plus same guard.
| Music condition | Max sample dBFS | Max independent 16x estimate | Median RMS gain dB |
|---|---:|---:|---:|
| raw_four_bank | 10.286 | 10.289 | 0.000 |
| sample_budget | -1.000 | 0.099 | -2.293 |
| raw_plus_prefix | -1.227 | -1.087 | -3.447 |
| budget_plus_prefix | -1.222 | -1.013 | -3.132 |
Raw four-bank +10.286dBFS -> budget -1dBFS sample ceiling. Still one of nine music excerpts above full scale in independent 16x estimate (+.099dBFS), so the budget does not replace lookahead. Both guarded modes zero full-scale overload across vocals and music. Budget+guard retains paired median .315dB more music RMS than guard alone, but budget decreases median paired music tail RMS by 1.661dB. Vocal median tail unchanged. Need listening and transient-sensitive allocation. No host tempo test.

## Symmetric FIR optimization

New 4x split 40-span candidate pairs symmetric downsampling coefficients, averaged in prepare, adds two samples before multiplication, preserves linear-phase alignment. Mathematical filter design essentially unchanged but arithmetic reordering is **not bit exact**. Stress max absolute error 2.443e-15 (6 rates, 3 drives, 3 mixes, reset); dry exact. All 45 audio pairs in 3 repetitions maximum error 2.887e-15; 40-sample latency. Paired median native timing reduction 17.63% vocals and 15.94% music, 35/36 and 9/9 faster. No new multistage design or alias sweep; no production change, no DAW CPU guarantee.

## Presence playback repair

Prior private self-contained HTML used FLAC data URLs and readiness timed out. Re-encode 15 embedded FLACs to 24-bit PCM WAV with SoundFile, all decoded samples exactly identical, source sample rates preserved. Store base64 WAV payloads locally; create an audio/wav Blob URL on selection, pause/remove old source, revoke previous URL, attach metadata/error handler before source and load, call play in click handler, clamp restored time to duration, invalidate stale callback by token. Reset comparison removes source and revokes URL. Defer export URL revoke after click. Private v2 HTML digest and size in JSON; no private audio/HTML in repository. Chromium Playwright set_content test with explicit no-user-gesture-required policy flag: selected A advances playback, switched B retains position (~.616s), comparison reset removes src, all six automated tie test votes exported valid JSON, zero page errors. These are artificial test votes, not listening preferences; user's actual app/local file navigation not tested. Subjective listening remains open. WAV document 49.4 MB; original private HTML preserved.

## Pitch and actual host

Recovered corresponding source archive and pinned verified offline JUCE 8.0.12 plus isolated overlay. ALSA/Freetype/Fontconfig/GL pkg-config probes pass. GTK/WebKit missing. Configured archived Playground with SKELLY_META_TEST/BUILD_PITCH_PLAYGROUND/PLAYGROUND_FULL ON, exact SnapCore header, Meta source, JUCE_PATH and local SkellCore FetchContent source, disconnected. Two attempts timed out at Building juceaide; partial build cache retained (11MiB at last check). No full fifth-engine render, actual VST3 host, FL Studio or native UI inspection. Archive source not proven equivalent to latest full branch. Do not replace protected Classic/Crystal. No new compression transient discriminator or isolated instrument validation, and no new multistage filter architecture. Static vendor backlog 854/90/692 unchanged.

## Reproduce
Compile tests/test_budget_quiet_symmetric.cpp C++17 O3 and ASan/UBSan. Initial compile failed missing includes, corrected and reran. Run benchmarks/owned_budget_quiet_symmetric.py --manifest /private/vocals.json --output /private/batch.json --start 0 --count 9 --tones; starts 9/18/27 without tones. For music use --music --start 0/1/2 --count 1. All batches complete, source SHA exact 8/8, private report digest in adjacent aggregate. New CI registered; latest commit verification pending. No merge.
