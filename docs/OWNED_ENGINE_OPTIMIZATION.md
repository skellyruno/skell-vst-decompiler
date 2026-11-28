# Owned DSP optimization, coverage and chain headroom — 2026-11-25

Parent `602ad1968ae9649fe54cf1ce89663997bb3b1870`: all eight workflows passed. Existing sources unchanged. No new vendor disassembly or reconstruction.

## Optimizations
SpacerStereoSIMD uses stereo double SSE2 lanes, per-lane attack/release selection and denormal guard masks; falls back to the existing scalar class on other architectures. ColorContiguousFixed mirrors input/output ring history to remove wrap branches from each FIR tap; this doubles the ring memory, retains the same coefficients, summation order, mix and 40-sample dry delay. Both are independent optimizations of existing original Skell research, not third-party implementations.

240,000 seeded frames per case; 4 rates and both LR/MS for Spacer, both 2x/4x for Color. Measured maximum sample error zero in this build. Separate impulse tests: no initial dry delay in Spacer, 40 samples at Color mix=0. Local median from three runs, pre-generated input, Xeon Platinum 8573C/g++14.2: Spacer 17.676938 -> 8.629307 us/48 stereo frames; 4x color 35.427411 -> 29.609945. Not a DAW benchmark; no host performance claim.

## Held-out grid
36 tone frequencies at each of 44.1/48/96/192 kHz. Same frequency main (.25 peak) and left-only detector (.5 peak), 1-second input, last half measured by RMS, independent right error and in-phase projection. In tested 63–16000 Hz grid, weakest cut -4.539456 dB at 13454 Hz/192 kHz. At 30 Hz cut only ~0.061 dB; bank needs better edge coverage. This is not a continuous-frequency response or a cross-frequency collateral matrix.

## Chain
Original Presence -> ProgramLeveler -> contiguous 4x Color. Two seconds of independent multitone, stepped envelope and transients at each sample rate. Color stage sample peaks 1.1755/1.1511/1.3190/1.3873. Approximate 4x interpolated peaks 1.2617/1.2466/1.3198/1.3881. Fixed -3 dB post trim produces estimated peaks .8932/.8825/.9343/.9827 on this test only; no general peak guarantee, no certified true peak. Explicit trim is a diagnostic comparison, not approved production sound. Color still needs a separately verified limiter strategy and real music comparisons.

## Verification
9/9 existing focused Python tests passed. Optimized four-rate parity/coverage/chain passed. Initial exhaustive sanitizer run exceeded local time limit; rerun with 12k frames per case at four rates passed. 48 kHz coverage/chain ASan/UBSan passed and outputs matched optimized bytes. Five local tested Git blobs matched staged tree. Current CI pending. JUCE remote lookup failed DNS; no UI edits, Quick4, Windows, FL Studio, vendor/reference renders or production changes. Preserve draft.

See reports/owned_engine_optimization_2026_11_25.json and tests/coverage_and_chain_smoke.py. Next: independent additional edge bands, cross-frequency sweep, automation/CPU, original peak-safe limiter integration and authorized matched real-audio tests.
