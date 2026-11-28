# Integrated system identification, second round

Prior 027a4f501eedcb6dba9c33015c0f7717d8f5e5ef: 179 regression tests and all eight workflows passed. The Ghidra high-P-code smoke is now actually verified: owned fixture smooth reports FLOAT_ADD, FLOAT_SUB, FLOAT_MULT and three definition edges; apply_gain reports CALL, FLOAT_MULT and two definition edges. This is verification of aggregate high-P-code extraction on owned code, not decompilation of the three vendor targets. Previous 27,707 chained-unwind relationships remain verified metadata, not runtime paths.

## Audio measurement
Preserve the previous 11 original probes. The new system_id generator adds five files at 44.1/48/96 kHz: three distinct dynamic histories and two one-channel-at-a-time log sweeps with a one-second zero tail. Train on the first history only, select descriptive models by validation, keep the third history separate. Source and output hash, sample-rate, declared alignment and settings checks use reference_lab. Peak of generated histories below full scale at all three rates. Source level rounding to 0.01 dB is only for intended coherent constant-level histories.

Five new system-id regression tests, two detector/bridge tests, syntax checks and an actual built-in Pedalboard 0.9.23 native compressor smoke passed locally. Known discrete single and dual controls recover 160/800 ms release with heldout error below 1e-6 dB. On a known 0.5 + 0.25 z^-1 FIR, magnitude and phase agree to four decimal places at ten selected frequencies. The stationary synthetic vowel resonance candidates are 714.166, 1189.386 and 2502.797 Hz for 700, 1200 and 2500 Hz generators. LPC bandwidths may be inaccurate; no actual vocal formant preservation claim. Sweep transfer assumes LTI response contained in recorded tail, not general nonlinear deconvolution.

## Real independent native calibration
No target VST loaded. Three original WAV histories processed by built-in Pedalboard Compressor 0.9.23 at 48 kHz, threshold -24 dB, ratio 4, attack 20 ms, release 160 ms. Separate gain-domain single/dual and detector-domain amplitude/power models fitted by bounded numerical least squares. Detector integrates predicted gain at 1 ms substeps and averages gain power over 10 ms. Different timing conventions and RMS/peak detection prevent interpreting fitted parameters as exact knobs.

| Model | Train RMSE dB | Validation RMSE dB | Final test RMSE dB |
|---|---:|---:|---:|
| Single gain | .407698 | .356893 | .376848 |
| Dual gain | .437367 | .401587 | .442093 |
| Amplitude detector | .070302 | .099806 | .078675 |
| Power detector | .131467 | .132288 | .134193 |

Amplitude model selected by validation; final test error about 79% lower than single-stage gain comparator. This calibration shows that competing signal-domain hypotheses matter, not that the native implementation or vendor architecture has been recovered. Small local minima in dual model fit possible; no global optimum guarantee. Separate real performances and plugin settings still required. Numeric least-squares optimization is not full differentiable neural waveform fitting.

## Commands
    python -m skell_vst_decompiler.system_id generate probes_extended
    python -m skell_vst_decompiler.system_id analyze probes_extended dynamic_train wet.wav metadata.json > train.json
    python -m skell_vst_decompiler.system_id analyze probes_extended dynamic_holdout wet2.wav metadata2.json > validation.json
    python -m skell_vst_decompiler.system_id analyze probes_extended dynamic_test wet3.wav metadata3.json > test.json
    python -m skell_vst_decompiler.detector_fit train.json validation.json test.json

Use system_id analyze on sweep_left_tail/sweep_right_tail for LTI response and on the original vowel_like probe for LPC candidates. For candidate comparison, set an explicit identical target_stage in both render metadata files:
    python -m skell_vst_decompiler.listening_bridge probes_extended dynamic_test reference.wav candidate.wav reference.json candidate.json

Optional --sound-match and --fif-signal call the existing Sound Match quality_gate.measure and vocal_knob_search.fif_ears_signal_snapshot APIs inspected at 810e387c5736791469a0a3e4e877ecd259b8aa7b. Require the separately installed packages. Base aligned comparison and mismatched-stage rejection passed; optional imports unavailable locally, not verified. No auto approval, no tempo/key or private data upload. Keep all private render files outside Git. CI adds pinned Pedalboard native smoke.

## Remaining
Actual authorized target outputs for TVB, VMR and Evo, runtime observation in a legitimate host, target-specific parameter mapping, more complete mathematical dataflow, independent real-performance validation, waveform-level differentiable modeling and native C++ implementation/CPU checks remain open. No new vendor disassembly, no proprietary code reconstruction or production plugin changes this round. See reports/system_id_validation_2026-11-24.json.
