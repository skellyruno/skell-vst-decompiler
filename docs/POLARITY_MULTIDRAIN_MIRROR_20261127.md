# Polarity-aware reconstruction, four-bank scheduling and exact FIR optimization — 2026-11-27

Parent 32b090c4b7c85986ffdedad720d9715281a4c575; previous eight CI workflows passed. Reused latest identified offline kit, 13/13 checksums passed. Reverified source hashes of 36 prior private vocal excerpts (2 archive-labeled dry, 34 processed) and three existing private beat files. Nine predeclared ten-second music excerpts, 90 seconds total; correlated within each source. No new vendor binary traversal, execution, private audio publication or production changes.

## Polarity-aware bound
Let w_j be the signed tap/sample product, g_j the nonnegative linked gain with upper bound G for the window, r the fixed release pole, and m_j=max_{k>=j}g_k. The release rule g_(j+1)<=r*g_j+1-r implies 0<=m_j-g_j<=1-r^(last-j). Since m_j is nonincreasing, summation by parts bounds the positive weighted sum by G times the maximum nonnegative prefix sum, and the negative direction by G times the maximum nonnegative negative prefix. The error from replacing g with m is bounded separately in each direction: positive output uses only negative tap/sample products weighted by the release deficit; negative output uses only positive products. Compute a safe gain cap for each polarity using its signed-lobe bound and its prefix/error bound, choose the larger independently valid cap for that polarity, then the minimum across both polarities, channels, phases and all contributing windows. Exponential deficit weights are precomputed in prepare. This retains the 16-sample lookahead and same finite four-phase reconstruction kernel.

Six sample rates (8/44.1/48/96/192/384k), three release settings and three stress families, 7,160,832 bounded channel/phase checks per optimized and sanitizer run. Max bounded linear magnitude .891250938134 (-1dBFS); old signed predictor .922444108097. All four bounded designs pass. Independent 16x Kaiser reconstruction estimates are NOT certified true peak. Worst observed vocal estimate for new design at 1ms is -.696dBFS, above the nominal -1 target but below full scale.

| Release ms | Vocal paired median RMS advantage dB | Music paired median RMS advantage dB |
|---:|---:|---:|
| 1 | 0.6295 | 1.3747 |
| 60 | 0.0199 | 0.0323 |
| 1000 | 0.0016 | 0.0021 |

270 limiter renders (45 excerpts x 2 algorithms x 3 releases), all finite, zero estimated full-scale overloads. The larger benefit is at fast release; at 60ms and 1000ms marginal. Three alternating paired timing repetitions at 60ms, output allocated before clock, includes prepare; median paired time increase 12.02% vocals, 12.42% music. Candidate is not a CPU optimization over release-prefix. Do not select fast release solely for RMS preservation; modulation distortion and listening remain open.

## Four-bank draining schedule
Independent fixed second-order allpass feedback banks, 25ms input routing fade, retiring bank drains with no new input. On capacity pressure, choose draining bank with smallest remaining lifetime (source comment says oldest; actual criterion is remaining lifetime), shorten retirement to 25ms smooth fade, then reuse after free. Latest request wins, no process allocation/history clearing. Four preallocated rings double history storage vs two-bank mode. At maximum 384k/4s configuration, about 93.75MiB ring storage alone assuming 16-byte stereo Frame. Not a production memory decision. Nominal -60dB recurrence expiry is not a hard amplitude guarantee.

60 exact old-echo checks across six rates. Stress .95 feedback with changes every 75ms: max pending wait 24.997396ms, 48 forced retirements total, exact dry and finite output. Optimized and ASan/UBSan pass. On 36 vocals and nine mixed-music excerpts, 250ms fixed request interval including appended silence, .7 feedback, requests cycle 90/105/120/135/150ms plus half sample. Accepted means active target equals the current request before supersession, including possible already-active targets; does not mean audible arrival. Wait only among accepted requests.

| Corpus | Two-bank accepted | Four-bank accepted | Four-bank forced retirement | Worst raw four-bank sample peak |
|---|---:|---:|---:|---:|
| Vocals | 160/648 | 646/648 | 540 | +4.523 dBFS |
| Music | 90/360 | 360/360 | 333 | +10.286 dBFS |

Max accepted wait on four banks 25.011ms vocals, 25ms music; two-bank 203.356/203.063ms. Median paired tail RMS improvement over 250ms appended silence +.065dB vocals/+1.121dB music. Forced retirement shortens old tails, and high summed output is a serious drawback. Post-delay polarity guard (16 samples) yields zero independent 16x estimated full-scale overloads across all 90 delay outputs; worst four-bank music estimate -1.058dBFS, worst RMS attenuation 5.597dB. Not a substitute for better wet gain budgeting; no DAW tempo or transport automation validation.

## Exact FIR indexing optimization
ColorSplitMirrored is a separate copy of existing native split FIR with input/output histories mirrored and descending contiguous indexes. Coefficients, sample order and arithmetic accumulation order unchanged; no fast-math flag. No change to production or existing lab class. Extra history storage 3232 bytes at 4x span40 (41+161 extra stereo double frames), same 40-sample latency.

Optimized and sanitized six-rate parity regression: 1,769,472 exact channel comparisons per run over 2x/4x, span40/80, equal/split cutoffs, 0/50/100% wet, 0/12/24dB drive, NaN sanitization and reset. All 45 real excerpts exact numeric equality in three paired repetitions (22,685,858 channel samples per repetition). Not a cross-compiler bit-identity guarantee.

| Corpus | Original median ms/audio-second | Mirrored median | Median paired time change |
|---|---:|---:|---:|
| Vocals | 18.0436 | 17.5899 | -2.4088% |
| Music | 21.0206 | 21.0759 | -2.8382% |

Individual medians and median paired ratios differ. Faster 30/36 vocal and 7/9 music excerpt pairs. Modest speedup, setup included and other batches concurrent; no actual DAW CPU claim or spectral improvement.

## Reproduction and remaining gates
Compile tests/test_polarity_peak.cpp, test_multi_drain.cpp, test_color_mirrored.cpp with GCC C++17 O3 and ASan/UBSan; added regression CI step. Run benchmarks/owned_polarity_multidrain.py --manifest /private/vocals.json --output /private/batch.json --start 0 --count 9, repeat starts 9/18/27; music use --music --count 1 and starts 0/1/2. Initial combined music run timed out before final JSON, discarded; split runs completed all nine. Run benchmarks/owned_color_mirrored.py for both private manifests, music add --music. NumPy, SciPy, SoundFile required. Preserve private manifests/rows/audio locally; aggregate report includes exact source blobs and full private report digest. New hosted CI pending. No new compressor isolated stems, presence playback, pitch challenger, vendor replay, Windows VST3 or UI/DAW verification. Static backlog remains 854/90/692. All approved engines/presets/defaults untouched.
