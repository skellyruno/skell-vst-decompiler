# Skell DSP reference laboratory — first integrated round

Prior b2764112fa0b28845c6a06e6b5efd3bdb0cd18f6 passed 173 regression tests and all eight workflows. Continue previous original DSP prototypes and static research; do not replace them. No vendor implementation, original binary or private audio is exported to Git/CI.

## Read-only metadata

Six exact reference fingerprints matched locally; VMR split archive verified before reading the FG-2A member. Based on Microsoft's public x64 exception handling description (https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64), parse bounded v1 chained unwind metadata, correctly round the unwind-code slot count, require parent table membership, reject cycles/invalid chain flags, report unsupported versions and depth limits. All 27,707 chain-flag records in five x64 targets reach a nonchained v1 table record: TVB 11,314; rack 5,368; FG-116 3,706; FG-2A 3,594; FG-Stress 3,725. No invalid chains under this model. Evo x86 not applicable. Root relationships support compiler-fragment grouping but do not establish full functions, runtime control-flow, or DSP equations. No new instruction decoding in this round. The earlier 595 unconfirmed FG-2A observations remain unconfirmed.

## Reference WAV workflow

Generate 11 original synthetic stimuli at 44.1, 48 or 96 kHz; generation verified finite and peak-bounded at all three rates. 48k pack created and CRC, header, frame counts and source hashes checked. Use from checkout:

    python -m skell_vst_decompiler.reference_lab generate probes_48k
    python -m skell_vst_decompiler.reference_lab measure probes_48k levels_train path/to/wet.wav metadata.json > train.json
    python -m skell_vst_decompiler.reference_lab measure probes_48k levels_holdout path/to/wet.wav metadata.json > holdout.json
    python -m skell_vst_decompiler.reference_lab fit train.json holdout.json

Metadata keys: plugin, version, settings (full settings/host/routing string), source_sha256, render_sha256, offset_samples (explicit extra nonnegative transport delay; do not remove creative delay). Require two-channel sample-aligned renders; no automatic alignment or authentication of operator declarations. Check source and output hashes, rate, frames, channels, finite samples, and changed inputs. Render each case from reset state, same settings for fitting and holdout, no normalization or additional effects. Retain original files outside repo. Source hash alone is not evidence of pairing.

- TVB: isolate each effect, measure neutral control and individual settings, level/impulse/history/stereo/two-tone.
- VMR: one module at a time; distinct level training and held-out levels, short/long history steps, stereo detector and intermodulation.
- Evo: pitch steps, vibrato, glide, synthetic vowel-like input; document note mask, key, retune, input type, formant and Humanize. Mono routing explicitly documented if duplicated to stereo. Real human performances reserved for independent validation.
- Measurements: 10 ms RMS gain traces, stable RMS levels, hard-knee descriptive fit, selected coherent IMD, four-frequency stereo impulse responses (half-second windows; LTI only), left-channel 65ms F0 windows/10ms hop using existing FFT detector. Frame-end timestamp does not establish plugin latency. Sweep and vowel probes provided; complete sweep deconvolution and formant extraction not yet implemented.

Known synthetic WAV fixtures: hard-knee threshold -24 dB RMS, 4:1, makeup +2 dB; recovered -24.000000067 dB, ratio 4.000000076, makeup 2.000000052 dB. Held-out RMSE 6.483e-8 dB vs constant-gain 5.3133 dB. Independently generated 150 ms release measured 150.0065 ms from gain trace in regression; separately synthesized +100 cent pitch steps measured median 100.0022 cents, max stable error .01352 cents. These calibrate analysis only, not actual plugin parity. Six focused tests passed, including wrong-hash rejection, offset length mismatch, silent IMD undefined, cycles and malformed metadata. Exact tested source hashes retained.

## P-code path

New bounded aggregate Ghidra high-P-code script counts opcodes and input definition edges, without exporting operand data, pseudocode or constants. Uses documented HighFunction/PcodeOp APIs (https://ghidra.re/ghidra_docs/api/ghidra/program/model/pcode/HighFunction.html). Added owned compiled fixture smoke requiring known FLOAT_ADD/SUB/MULT, CALL and nonempty definition edges. Python syntax verified; Java/Ghidra execution unverified locally, CI required. Existing headless exporter preserved. No proprietary target decompilation in this step.

## Remaining gates

Obtain authorized aligned renders from actual reference plugins; use same settings and reset protocol; validate dynamics and pitch model on held-out real performances, then evaluate independent candidates with real audio, CPU/latency and host tests. Integrate Sound Match/FIF Ears only after schema and evidence matching. Full data-flow interpretation, formants, sweep deconvolution, differential optimization and actual host runtime observation remain open. No new production DSP or VST3 built. New CI pending.
