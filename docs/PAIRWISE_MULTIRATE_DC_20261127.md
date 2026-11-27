# Pairwise recovery, high-rate reference and lifted DC blocker — 2026-11-27

Parent a1204e285a4e39884e841e0f62113ed45015c47b. Prior Decompiler CI 8/8 and Core e3c9a51 CI 4/4. Latest cached Quick4 kit restored and 13/13 checksums verified; prior build cache absent. All 36 private vocal byte hashes matched previous manifest. Three original MP3s fingerprinted locally, not compared to a prior MP3 hash manifest. Same cohort, correlated excerpts; no isolated stems or private media committed.

## Pairwise recovery dual
For signed weights w and gain cap G, gains satisfy 0<=g_i<=G and g_j<=P*g_i+1-P for i<j, where P is the product of recovery poles from i+1 through j. When w_i<0 and w_j>0, choose lambda=min(w_j,-w_i/P). Substitute lambda*g_j by lambda*P*g_i+lambda*(1-P). Update weights and accumulate the constant. Remaining positive weights times G plus the constant upper-bound the weighted sum. Combine independently valid old and pairwise caps by max per signed direction, then min across phases/channels. Greedy reverse-order pairing is not optimality proof. Floating-point margin and streaming implementation remain required.
128 random windows, 58 limiting, all 58 improved; median +.148 dB. 144 peak-centered windows from 36 saturated vocals, 85 limiting, 81 improved; median +.599 dB, max +.728 dB. Independent LP oracle checked 2432 signed constraints/solves, maximum .8912509381337457 under declared -1dBFS finite-kernel ceiling within tolerance. No actual loudness or native output claim.

## Higher-rate saturation reference
54 single/two-tone settings x5 =270 renders; 36 centered vocal excerpts x5 =180. Compared 4x Blackman, 4x Kaiser10, 8x Blackman (all 40 sample span, .45/.475 normalized cutoff), and 16x/32x wider reference (.47/.49, span160, alignment compensated). Worst 16x-vs-32x tone matched difference -127.488 dB. Median vocal difference against wide reference -50.567/-50.447/-50.567 dB respectively for first three candidates. Filter coloration and aliasing both contribute; not pure alias error.
Same-filter isolation: identical normalized Blackman window/cutoffs/span, 4/8/16/32x. FFT decimation vs direct upfirdn max abs error 5.551e-15. 216 tone renders and 180 real excerpt renders (36 vocals and 9 music excerpts). Median matched differences against 32x:
| Corpus | 4x | 8x | 16x |
|---|---:|---:|---:|
| Tones | -108.643 | -121.575 | -135.558 |
| Vocals | -120.592 | -133.067 | -147.049 |
| Music | -127.566 | -140.042 | -154.024 |
8x closer on every tone and audio excerpt. Worst tone -42.100 vs -78.562 dB. These differences include sampled FIR and rate-dependent DC path, not just nonlinear aliases.

## DC ablation and lifted DC identity
11 source subset (2 dry, 6 processed by stable ID order, 3 music), 99 renders. Median 4x vs same-mode 32x matched difference: linear -194.070dB; nonlinear without DC -179.100dB; full nonlinear -127.778dB. The DC path is a major contributor to tiny numerical differences in this subset. Do not remove protection.
For H(z)=(1-z^-1)/(1-p*z^-1), p=exp(-2*pi*5/(M*fs)), multiply numerator and denominator by sum of (p*z^-1)^k, k=0..M-1. Denominator becomes 1-p^M*z^-M, numerator B=(1-z^-1)*sum. Convolve decimation FIR Q with B, decimate by M, then apply base-rate denominator 1-p^M*z^-1. Fixed parameters and zero initial states give exact-arithmetic equivalence; floating point is not bit-exact. Recursive updates reduce from M to one per base sample, FIR taps 161->165 (4x) or 321->329 (8x) and symmetry is lost. Net CPU savings not established.
96 stress conditions (6 rates x4 factors x4 signals), max error 1.558e-12. 90 real audio pairs (45 excerpts x4x/8x), max 4x vocal/music 1.255e-14/1.465e-14, 8x 2.220e-14/2.753e-14. Includes startup and alignment prefix; arbitrary state, full tails, automation, native implementation and speed untested.

## Reproduction and limitations
Run benchmarks/alias_reference.py, pair_bound.py, factor_isolation.py, dc_isolation.py, lifted_dc.py with authorized private --manifest and --output. NumPy, SciPy and SoundFile. Manifest inputs have id/stage/path/sha256. Pair bound and alias reference use vocal-only manifest, factor/lifted use combined vocal and three music sources, DC uses described subset. All completed locally, five exact Git blobs verified. Aggregate results and private report hashes only. No new C++ integration, hosted regression registration, vendor replay, full pitch build, UI or DAW testing. Static backlog 854/90/692 unchanged. No approved production changes; new CI unverified.
