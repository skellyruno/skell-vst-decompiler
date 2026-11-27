# Owned mask diagnostics and saturation tradeoffs — 2026-11-26

Parent ea7697dfcf19b5f602e0387e3257e3f800849acc. Cached offline kit manifest 13/13 passed; exact previous independent engine and benchmark source blobs checked before changes. This is an owned lab milestone, not a vendor algorithm reconstruction or production UI/engine change.

## Clipping false negative

The source-known clip routine compiles to SSE compare masks and bitwise selection; the old arithmetic store tracker reports zero transformations. New original mask_diagnostic.py verifies narrow register-only legacy SSE comparison predicates and bitwise operands against both raw decoders, tracks copied comparison tags and opposite-polarity terms, and reports local complementary-mask OR candidates. Unknown instructions, memory operations, gaps and supplied entry guards clear tags. Scalar masks describe only the scalar lane; selection tags are not numerical or audio-role proof. Reran the existing owned context benchmark with the additional diagnostic: one scalar select at O1 and two packed plus one scalar at O3; none in the other 16 owned regions. The clear-control routine has one bitwise op at O3 but no select candidate. No change to prior vendor candidate counts.

## Extended saturation sweep

Six coherent frequencies 1000/3004/7004/11004/17004/20004 Hz, peak amplitudes .1/.5/.9, three rates 44.1/48/96 kHz, original 1x/2x/4x prototypes. One second warmup and quarter-second measurement. 54 stimulus settings / 162 renders. Residual is integrated nonharmonic-bin energy relative to fundamental, excludes DC and integer in-band harmonics; aliases overlapping those bins are not measured. Analytical tests validate even/odd FFT lengths, known harmonics, residual and Nyquist energy. Initial odd-length endpoint weighting was corrected before rerun. Both oversampled variants lowered measured residual at all 54 settings; 4x lower than 2x at 45/54. This is not an exhaustive alias metric or perceptual result.

| Rate | Median residual 1x/2x/4x dBc | Worst residual 1x/2x/4x dBc |
|---|---|---|
| 44100 | -35.54 / -79.92 / -126.71 | -10.98 / -19.81 / -42.11 |
| 48000 | -35.54 / -73.29 / -108.05 | -10.98 / -19.80 / -35.99 |
| 96000 | -39.32 / -115.90 / -115.92 | -10.98 / -34.02 / -68.59 |

At 44.1 kHz the largest tested attenuation relative to 1x was approximately 14 dB for both oversampled variants. Timing: five repeats of one second of generated stereo two-tone input per engine/rate, block 256, includes native adapter and preparation, excludes Python array allocation and finite checks. 75 timed runs. At 48 kHz medians for presence, leveler, color, 2x, 4x were 1.55, 1.40, 1.82, 11.61, 23.92 ms per second of audio. Hardware AMD EPYC 9V74, 5 visible logical CPUs, Linux x86_64 GCC 14.2. These are container wall-time results, not FL Studio CPU or real-time guarantees.

## Experimental cutoff and span

Parameterized the existing lab template with bounded even BaseSpan and CutoffMilli; defaults remain 40 and 450. Existing named aliases unchanged in configuration. Native adapter built before this edit and compared to new defaults on all 72 wet stimulus/engine combinations; every sample was exactly equal. Six variants, 36 settings, 216 renders, 18 exact dry impulse delay checks, 90 additional timed runs. Higher cutoff .475 versus .450, spans 40/80; span is the expected dry delay in samples.

At 44.1 kHz, 20004 Hz, .5 peak, 12 dB drive, fully wet:

| Variant | Gain relative to same-factor default | Nonharmonic residual dBc | Dry delay samples |
|---|---:|---:|---:|
| 2x .450 span40 | 0 | -41.14 | 40 |
| 4x .450 span40 | 0 | -77.89 | 40 |
| 2x .475 span40 | +8.39 | -30.68 | 40 |
| 4x .475 span40 | +8.39 | -59.78 | 40 |
| 2x .475 span80 | +10.37 | -28.61 | 80 |
| 4x .475 span80 | +10.37 | -54.05 | 80 |

Broader cutoff restores high-frequency level but worsens residual on this stimulus. Longer span further increases level but latency and cost; not uniformly better. At 48 kHz default 4x median 21.81 ms per audio second versus 36.33 ms for .475/span80. No variant selected for production; keep defaults. The parameterization is an experimental header-only source change, not a promise of ABI compatibility for separately compiled template instantiations.

## Validation / reproduce

25 targeted unittest methods passed locally, six new (three mask, three spectral); NumPy tests explicitly skip if dependency unavailable in CI, and were executed locally. Owned context benchmark rerun and passed. Exact eight tested source Git blobs recorded. To reproduce on Linux with GCC/Clang/LLD, GNU/LLVM objdump, Python and NumPy:
- `python -m unittest discover -s tests -p 'test_*.py'`
- `python benchmarks/owned_context_audio.py --output context.json`
- `python benchmarks/owned_extended_audio.py --output sweep.json`
- `python benchmarks/owned_color_tradeoff.py --output variants.json` (optional --old-adapter points to an explicitly owned baseline compiled from parent header and adapter; never load a vendor binary).
Full local report SHA-256 values recorded in JSON. Parent CI status recorded; new full CI not yet verified. No vendor execution, real music or vendor equivalence, host integration, true peak, general alias/CPU claims. Existing 692 candidates, 854 unresolved destinations, 90 boundary conflicts unchanged. No production changes.
