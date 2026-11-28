# Release-constrained reconstruction bounds, draining delay and mixed music

Parent ca1f2a95a027b251b1b3851b4151a9bce47d629a; previous CI 8/8 passed. Cached Quick4 manifest 13/13 verified. Exact owned baseline and new source Git blobs verified. No vendor binary replay, production engine changes or private media committed.

## Limiting: retain cancellation with a rigorous finite-kernel bound

The previous signed predictor is not a guarantee: gain changes inside the reconstruction window can destroy cancellation. With the existing 17-sample four-phase kernel, let w_j be the kernel tap times the input sample in one channel. For gain 0 <= g_j <= G, the weighted sum is bounded by G times max(sum of positive weights, sum of absolute negative weights). This is tighter than summing all absolute weights. Also, the existing release law ensures g_(j+1)-g_j <= delta=1-releasePole. Define m_j=max of gains from j through the last sample. Then m is nonincreasing, 0<=m<=G, and m_j-g_j <= (last-j)*delta. By summation by parts the weighted sum with m is bounded by G*max absolute prefix sum of w. The residual is bounded by delta*sum((last-j)*abs(w_j)). Compute a gain cap from each independently valid bound, choose the largest safe cap per phase/channel, then the minimum across phases/channels and all windows contributing to the output sample. The declared reconstruction ceiling follows for bounded finite input within floating-point tolerance, not for arbitrary reconstruction filters. Release coefficient fixed during processing. Keep 16 sample latency and no process allocations.

Native stress: 6 rates x 3 releases x 3 signal families, 5,370,624 bounded channel/phase checks per run, optimized and ASan/UBSan passed. Maximum bounded reconstructed magnitude .891250938134 (-1dBFS); old signed predictor .922444108097 (-.7012dBFS), confirming the limitation. Exact delayed low-level signal test passed. Replaced circular indexing in hot loop with mirrored ring, compile-time mode specialization, direct phase-zero center tap, fused channel accumulators. Reran all tests and 36-vocal benchmark; all recorded audio metrics unchanged exactly from initial implementation. This is measured metric parity, not a byte-identical waveform claim.

| Mode | Median RMS gain dB | Maximum independent 16x estimate dBFS | Native median ms/audio-second |
|---|---:|---:|---:|
| old_signed | -0.206 | -0.676 | 2.070 |
| old_absolute | -3.877 | -1.483 | 2.501 |
| new_absolute | -3.877 | -1.483 | 3.521 |
| signed_lobe | -1.984 | -1.111 | 3.395 |
| release_prefix | -0.642 | -0.879 | 10.407 |

All 36 vocals after fully wet 40-span split color; 180 guard renders per implementation. Release-prefix preserves median paired 3.248 dB more RMS than old absolute bound. Zero full-scale overloads in independent 16x estimates. Worst estimate -.879 dBFS exceeds nominal -1 target slightly, demonstrating why the finite-kernel guarantee is not a true-peak guarantee. Initial prefix wall time 15.878 vs optimized 10.407 ms/audio-second (separate concurrently batched runs, not paired CPU tests). Still slower than original predictor. No subjective approval.

## Delay: input routing rather than retiring old history immediately

DrainingDelay uses two fixed-coefficient second-order allpass feedback banks. On accepted time request, new bank starts immediately, route input by 25ms smoothstep, then feed zeros into old bank, sum both wet outputs while old tail decays. Nominal -60dB recurrence retirement time from feedback and old delay, plus guards/fade; not a strict amplitude bound for dispersive allpass. Final retirement fade reaches exactly zero. Additional requests coalesce until old bank is available. BPM helper bounds BPM/beat length and delay capacity; no transport integration. 60 exact integer old-echo checks (ten at each of six rates), finite stress at .95 feedback, exact dry and tempo mapping passed optimized/sanitizers. Initial test underestimated drain duration; corrected expected test duration and final fade, then reran.

36 verified vocals with same 120->180->90ms half-sample requests and 250ms appended silence as previous test. Draining raises median paired tail RMS by 2.617dB; greater tail on 34/36. Old output crossfade peak +3.025dBFS, draining +3.669; independent 16x peaks +3.090/+3.712. Both overload two excerpts. Appending release-prefix guard yields worst sample -1.816 and estimated16 -1.769dBFS, zero full-scale overload, five excerpts with measurable RMS attenuation (>1e-6dB), max loss 1.115dB, median zero. Guard adds 16 samples latency, not a production delay latency decision. First new bank accepted immediately vs previous active target after 207.914ms; not same audible event. Second request completed all 36 previous transitions but only 25/36 draining during observation, median 970.023ms delay among completed vs 117.914ms previous. Preserve as experimental tail-priority mode, not tempo-responsive default. Needs better bounded multi-bank scheduling, headroom and host automation validation.

## Real instrumental music: expand beyond vocals

Located three filename-labeled instrumental stereo MP3 beat files in connected Drive. Fingerprinted original bytes and decoded locally at native 48k. Three nonoverlapping ten-second excerpts per source at predetermined quarter/half/three-quarter positions = 90 seconds of real mixed music; excerpts within one source are correlated, not nine independent tracks. No isolated bass/drum labels confirmed. Test full mix plus separate causal 4th-order 120Hz lowpass/highpass diagnostic copies (not stems). Existing leveler 4ms vs fixed12/fixed20/adaptive at 7.828ms matched t90 from earlier step, 4:1, -18dB, 120ms release. 108 leveler renders. After RMS normalization:

| Input | Adaptive lower peak | Median paired peak delta dB | Median paired onset proxy delta dB |
|---|---:|---:|---:|
| full | 8/9 | -0.092 | 0.123 |
| lowpass_120hz | 9/9 | -0.752 | -0.233 |
| highpass_120hz | 9/9 | -0.845 | -0.110 |

Raw peaks lower 2/9 full, 8/9 lowpass, 5/9 highpass. Onset proxy selects top decile of input 5ms window peak rises, then RMS of output window peaks; positive full-mix delta may mean stronger attacks, not necessarily less distortion. Full-mix advantage modest; adaptive/fixed settings very similar. No replacement. Saturation four prior configurations each overload all nine excerpts by independent 16x estimate, worst +2.415dBFS for 40-span output-only split. Release-prefix guard on that split gives zero estimated overload, max -.999923dBFS and median -2.173dB RMS change. Real music challenges headroom more than the vocal corpus. No new spectral sweep, no isolation or listening claims.

## Remaining gates and reproduction

Presence private blind HTML: direct file navigation blocked by browser administrator policy. HTML set_content loaded controls, but embedded media readiness timed out. No verified playback/position synchronization/export or subjective votes from that test; no fake listening results. No new pitch challenger; previous four-engine portable comparison retained; fifth engine, approved Classic/Crystal, Chorus/Flang untouched. Local Linux pkg-config lacked several audio/GUI development entries, no actual VST3/Windows/FL Studio host built or run this batch. Native timings not DAW CPU. Vendor backlog 854/90/692 unchanged. New tests registered in CI; new CI pending.

Reproduce with GCC C++17 O3 and ASan/UBSan for tests/test_bounded_peak.cpp and tests/test_draining_delay.cpp. Run benchmarks/owned_bounded_peak.py and owned_draining_delay.py with --manifest /private/manifest.json --output /private/batch.json --start 0 --count 9, then 9/18/27; combine by unique input id and retain all rows privately. Run benchmarks/owned_mixed_music.py --manifest /private/beat-manifest.json --output /private/music.json on authorized files. NumPy, SoundFile, SciPy required. All source blobs in aggregate; only aggregate results and report digests stored in Git.
