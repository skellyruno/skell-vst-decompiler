# Sample-scheduled recovery bounds and stage-selectivity screen

Parent 01aa68f0a6ccf4e8d58c0a459895ebf0a22c7fb6. Cached Quick4 kit 13/13 verified. Reused 36 private fingerprinted vocal excerpts and nine ten-second excerpts from three prior beat files. No new independent performances, isolated stems, vendor replay or production engine changes.

## Scheduled recovery

Previous BassAwarePeakGuard precomputes the worst release deficit using its fastest possible fixed recovery pole. ScheduledRecoveryGuard computes exactly the same detector in input order, stores each sample's actual pole in a mirrored ring, and uses that stored pole when the sample leaves the existing 16-sample lookahead. For a window j..last, recovery satisfies g_k <= R_k*g_(k-1)+1-R_k, with R_k in [0,1]. By iterating, every subsequent gain is bounded by 1-(1-g_j)*product(R_(j+1)..R_k). Hence m_j-g_j <= 1-product(R_(j+1)..R_last), where m_j is the suffix maximum of the gain sequence. The suffix recurrence d_j=(1-R_(j+1))+R_(j+1)*d_(j+1) computes that bound with a small upward numerical margin. The existing polarity/prefix bound uses these tighter weights. Ring storage preserves alignment, no process allocation or extra PDC. Bounded finite inputs only; not a certified analog or true-peak guarantee.

Six rates, three base release settings, two ceilings (-1/-12dBFS), four stress regions, 4,621,824 declared-kernel checks per optimized and ASan/UBSan run, exact delayed low-level audio after reset. Maximum reconstructed magnitude .89125093813374567. Minimum observed gain difference vs prior -5.9952e-15 (roundoff), within 1e-12 tolerance. Initial compile warning from ambiguous one-line loop was corrected before passing both builds. Real-audio comparisons also checked candidate absolute output is not lower beyond 1e-12; 45 excerpts after identical symmetric color, same 1ms fastest pole, three alternating timing pairs.

| Corpus | Prior median RMS gain | Scheduled median RMS gain | Paired median advantage | Prior native ms/audio-second | Scheduled |
|---|---:|---:|---:|---:|---:|
| Vocals | -.303713 | -.303123 | +.000041dB | 4.4421 | 5.5917 |
| Music | -2.455533 | -1.967900 | +.499319dB | 8.2144 | 10.9209 |

Music gains improve in all nine excerpts, paired range +.1721 to +.6139 dB; 21/36 vocals improve by >1e-6dB, median negligible. Worst independent 16x peak estimate vocals -.696dBFS both, music -1.192 -> -.986dBFS. No full-scale estimates. Not a certified true-peak meter, and independent reconstruction can exceed declared kernel target. Paired native timing increases 22.49/30.19% vocals/music, includes prepare and concurrent batches, no host CPU claim.

16 tone settings, 32 native renders, at 48k, coherent final one-second measurement. At peak1.5, 20/30/50/100Hz harmonic-bin distortion prior -21.897/-24.265/-27.582/-16.450 dBc; scheduled -23.693/-26.121/-29.506/-17.393 dBc. Not a complete alias or listening metric. Keep as a higher-quality candidate, CPU still a drawback.

## Offline cascade filter selectivity

Screened 13 two-stage FIR designs plus same single-stage reference (45 conditions, 630 renders). All 40 base-rate sample alignment, same independent nonlinear transfer. Blackman 65/33 and 12 equiripple candidates: first/second taps 73/17,65/33,57/49,49/65; first up pass edge .205/.215/.225 cycles per stage sample, stop .275, stopband weights 1/3/10 respectively; first down pass edge min(.235,p+.0125), stop .275, equal weights. Second halfband Remez .19/.31, structural zeros enforced and DC normalization; Blackman reference cascade as previous. No native engine changes. Offline single-stage baseline matches previous native results within 5.33e-15dB fundamental and .000149dB absolute residual across the 45 settings (different numerical implementation). Nonharmonic residual excludes harmonic-coincident aliases and DC.

| Design | Near parity /45 | Strict improvement /45 | Worst residual increase dB | Minimum fundamental change dB |
|---|---:|---:|---:|---:|
| blackman_65_33 | 21 | 0 | 26.793 | -0.608 |
| eq_73_17_0.205_0.275_1 | 10 | 5 | 34.419 | 0.002 |
| eq_73_17_0.215_0.275_3 | 8 | 5 | 34.582 | 0.005 |
| eq_73_17_0.225_0.275_10 | 8 | 5 | 39.713 | 0.004 |
| eq_65_33_0.205_0.275_1 | 13 | 3 | 28.620 | -0.000 |
| eq_65_33_0.215_0.275_3 | 9 | 6 | 38.438 | -0.004 |
| eq_65_33_0.225_0.275_10 | 9 | 4 | 44.455 | -0.007 |
| eq_57_49_0.205_0.275_1 | 12 | 8 | 40.573 | -0.003 |
| eq_57_49_0.215_0.275_3 | 9 | 5 | 47.717 | -0.010 |
| eq_57_49_0.225_0.275_10 | 9 | 5 | 52.562 | -0.042 |
| eq_49_65_0.205_0.275_1 | 7 | 4 | 46.408 | 0.001 |
| eq_49_65_0.215_0.275_3 | 9 | 9 | 47.970 | -0.038 |
| eq_49_65_0.225_0.275_10 | 7 | 2 | 53.614 | -0.097 |

Near parity requires fundamental change >= -.1dB and residual increase <= .1dB; strict improvement requires >.01dB fundamental restoration and <=.1dB residual worsening. Best equiripple near parity only 13/45, worst residual +28.620dB; Blackman cascade 21/45, +26.793dB. More passband level does not guarantee lower nonlinear alias residue. No design meets full gate; retain current single-stage reference. No new native optimized cascade or musical adoption.

## Reproduction and limits
Run tests/test_scheduled_recovery.cpp C++17 optimized and ASan/UBSan with -ffp-contract=off (registered in CI). Run benchmarks/owned_scheduled_recovery.py on private fingerprinted manifests in batches --start 0/9/18/27 --count 9, --tones for first batch, music --music --start 0/1/2 --count 1. Run benchmarks/owned_cascade_selectivity.py --output local.json. NumPy/SciPy/SoundFile required. Aggregate and exact source hashes in adjacent JSON. All per-recording measurements and private audio stay local. Prior CI recorded in JSON; latest CI pending. No new compression/delay/presence subjective/pitch/actual host tests or UI changes. Static vendor backlog unchanged 854/90/692. No approved production changes.
