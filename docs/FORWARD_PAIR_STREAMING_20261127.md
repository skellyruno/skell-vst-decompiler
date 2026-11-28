# Native forward-stack pairwise reconstruction bound — 2026-11-27

Parent f9f0dff25aed303173025ee995a2b47cf3a1ae04; previous CI 8/8 passed. Reused verified cached Quick4 kit (13/13). All 39 local source fingerprints rechecked against prior manifest; 36 vocal excerpts and nine one-second music excerpts at three positions in each of three beat files. Same cohort, not independent held-out performances. Private media and individual rows stay outside Git.

## Method
For gain bounds 0<=g_i<=G and scheduled recovery g_j<=P*g_i+1-P (P the product of poles from i+1 to j), replace lambda of a later positive weight w_j by lambda*P at an earlier negative weight w_i and constant lambda*(1-P), lambda=min(w_j,-w_i/P). Unlike the prior reverse nested greedy search, forwardPairCap tracks previous negative residues on a fixed-size LIFO stack, uses prefix products for P, and consumes each negative or positive weight once. Work is O(N) in window length, no process allocation. Remaining positive mass times G plus constant bounds the signed reconstruction. Retain old bound as fallback; combine larger independently valid cap per polarity then minimum over channels/phases/windows. Tiny positive residuals are counted, discarded negative residues weaken the bound; use floating-point scale margin. Extreme weights or small product fall back. Exact-arithmetic argument assumes valid finite bounded inputs/poles, not a proof of arbitrary floating-point error or global LP optimality.

PairwiseScheduledGuard is separate from CachedScheduledGuard; same detector/recovery schedule, 16-sample delay, quiet-window gate, exact low-level delayed dry path. Pairwise bound evaluated only if old signed cap could reduce current window cap. No approved engine or preset changes.

## Verification
Optimized and ASan/UBSan runs each pass 960,000 sampled feasible-gain checks across six rates and two ceilings. Streaming regression each passes 2,373,120 declared-kernel checks across six rates, three releases, two ceilings, four stress regions. Max reconstructed .89124768725016845; minimum candidate-vs-old sample magnitude delta zero; reset/dry exact. Local CachedScheduledGuard and IndependentEngines headers match Git blobs; used a local kernel-only ReconstructionGuard shim reproducing the fetched kernel arithmetic, not full repository include graph. CI now registers both tests against full headers. All six tested source blobs match; benchmark path relocation hash verified, not rerun from full checkout. Independent LP oracle 256 randomized plus 180 selected peak-centered audio windows (3136 signed LP solves), no declared ceiling violation within tolerance. Vocal limiting windows 81/85 improved, median cap advantage .611dB; music 30/31 improved, .048dB. Window caps are not rendered loudness.

## Native real-audio results
45 one-second excerpts after identical offline 4x Blackman saturation (40 sample span .45/.475). Both native guards at same fastest 1ms recovery; each of three alternating paired repetitions checked no greater attenuation beyond 1e-12. Every output window including zero-padded boundaries checked against independent four-phase reconstruction kernel; no violation at -1dBFS. Independent 16x Kaiser estimates: zero full-scale overloads, not certified true peak.
| Corpus | Old median gain dB | New median gain dB | Paired median advantage | Old/new median ms/audio-sec | Paired time increase |
|---|---:|---:|---:|---:|---:|
| Vocals | -.3152 | -.1695 | +.1381dB | 5.5585 / 6.4523 | 16.25% |
| Music | -1.8012 | -1.7092 | +.0636dB | 11.4207 / 15.5485 | 30.31% |

33/36 vocals and 9/9 music improve >1e-6dB; max improvements .517/.304dB. Worst new independent 16x estimates -.733/-.995dBFS. Timing includes prepare and adapter; local wall time not DAW CPU. Quality candidate only; extra CPU is not justified for automatic default replacement. No new native lifted DC implementation, delay/compressor/pitch, actual VST3 host/UI, subjective listening or vendor static replay this batch. Backlog 854/90/692 unchanged.

## Reproduce
Compile tests/test_forward_pair.cpp and tests/test_forward_pair_stream.cpp with C++17 -O3 -ffp-contract=off -Iexperiments/engine_lab; repeat sanitizers. Run benchmarks/owned_forward_pair.py --manifest /private/combined.json --output /private/result.json using NumPy/SciPy/SoundFile. Aggregate and private report digest recorded adjacent. Latest hosted CI pending; no merge.
