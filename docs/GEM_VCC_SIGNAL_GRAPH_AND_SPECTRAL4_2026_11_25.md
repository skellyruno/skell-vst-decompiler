# Significant DSP evidence round: Gem Dopamine, VCC, and original Spectral4

2026-11-25. Exact read-only static analysis of user's supplied native binaries and independent Skell DSP experiments. Vendor binaries, code, calibration tables, audio and pseudocode remain private. This is NOT a reconstruction of proprietary source code or a demonstrated vendor-audio match.

## Gem Dopamine: significant multiband routing evidence

Source `Gem Dopamine-64.vst3` SHA-256 `dc923f6507cc891e0417854178f1db2eb84965040aa661c9c144649548dffb6f`.

- At RVA 0x58bbe0–0x58bef5, three **parallel** direct calls reach the previously confirmed five-term second-order IIR processing routine at 0x560150. They share the source buffer but use three distinct filter-state objects. This is not three serial filters.
- Vector difference/subtraction helpers at 0x561800 and 0x5615e0 create intermediate streams; four direct calls to 0x58c100 apply nonlinear envelope processing in 32-float blocks (four unrolled batches of eight). We have not mapped the four streams into an exact signal-reconstruction equation.
- Native coefficient generators 0x55f810–0x55f8d3 and 0x55f730–0x55f80a have canonical low-pass-like [1,2,1] and high-pass-like [1,-2,1] numerator shapes with double-precision normalization and float coefficient stores. These are verified structural classes; original coefficient tables are not distributed.
- The setup caller 0x58bf50–0x58c005 selects one positive-center setup and two negative-center setups, passing 3000 and 9000 scalar values to the latter. 44100 is observed in sample-rate setup. The resulting real cutoff frequencies and UI interpretation are **unverified**, and must not be reported as measured 3 kHz and 9 kHz cutoffs.
- Five candidate parameter indices at 0x58b750–0x58b912 include enable-like and gain conversions, but their host names and final runtime dispatch remain open.

## VCC Channel: eight three-stage dispatch configurations

Source `VCC Channel.epl` SHA-256 `73747020e8996938b8e6fdff51004cff4ea85c95f992cbc8bc0d0896a80aad87`.

Two wrapper candidates at 0x19ac10–0x19ae48 and 0x19ae50–0x19b085 refer to two hashed dispatch tables at RVAs 0xec0360 and 0xec0540. Each table contains 24 independently file-backed executable pointers grouped into eight triplets and 11 distinct targets. One wrapper selects and invokes three sequential stages; mode and a conditional flag contribute to the selector. The gain ramp around these calls is **not** proof of saturation. Specific saturation algorithms, mode names, valid runtime mode choices and exact host mappings are not yet established. Only hashes, counts and RVAs of these tables are published.

## Evidence

`reports/native_scoped/gem_vcc_deeper_signal_graph.json` stores 8 bounded byte-region SHA-256 hashes, **267 GNU/LLVM-agreed selected instruction checkpoints** (196 Gem, 71 VCC), 12 exact direct-call edges, 5 float constants, and 2 VCC dispatch table hashes. `skell_vst_decompiler/deep_signal_graph.py` verifies the original source fingerprint, code bytes, exact call target, float values and file-backed table entries, but does not execute plugins. Synthetic regressions reject wrong SHA, tampered region bytes, wrong call targets, scalars or tables. Three unselected padding/edge decoder differences were excluded from the agreement count (data16/nop, xchg/nop, rex./mov). Actual original sources passed both GNU and LLVM checks.

Reproduce locally:
```sh
python -m skell_vst_decompiler.deep_signal_graph '/private/Gem Dopamine-64.vst3' --report reports/native_scoped/gem_vcc_deeper_signal_graph.json
python -m skell_vst_decompiler.deep_signal_graph '/private/VCC Channel.epl' --report reports/native_scoped/gem_vcc_deeper_signal_graph.json --objdump llvm-objdump
```

## Original independent Spectral4 engine

`experiments/engine_lab/Spectral4.h` provides an original four-band stereo-linked dynamic processor, **not** Gem Dopamine's proprietary algorithm: three sequential double-Butterworth crossovers with telescoping residuals for perfect unity-band sum; independent per-band gain, common configurable threshold/depth, stereo-linked peak envelope, adjustable wet and final output trim. Coefficients prepared off the audio thread; `process()` does not allocate, lock or access files. Existing three C++ engines stay intact.

`experiments/engine_lab/test_spectral4.cpp`: g++ C++17 -O3 -Wall -Wextra -Werror and ASan/UBSan passed at 44.1/48/96/192 kHz. Unity response matched the input within 2e-11 in standalone tests; bypass mix=0 exact, reset deterministic, band boosts effective, finite outputs. +12 dB upper-band test at 12 kHz produced +12.0–12.3 dB; 100 Hz changed within 0.09 dB. Local optimized Linux measured ~2.1–2.4 microseconds per 48 stereo frames, synthetic and machine-dependent; NOT measured Windows VST3 CPU.

Real private owned `master test.wav` first 352800 frames/8 seconds/44.1 kHz: test with +8dB high band, depth .65 and no trim exceeded sample peak 1.0 (peak 1.469). Adding an explicit -5dB final trim in the same test yielded RMS .04957, sample peak .82628 and 4x intersample peak estimate .86725; source RMS .14140, peak 1.000, 4x estimate 1.04135. Zero NaNs, and unity-bypass was sample-identical. This **does not prove safe peaks on other material** and Spectral4 is **not a limiter**. Private audio never committed.

Archived local Python tests (older project snapshot) 82/82 passed including 3 new provenance tests. Native optimized tests and sanitizers passed. Parent `2fe9d83` all eight CI workflows passed; new exact-head full CI pending. No real vendor processing/audio parity, subjective A/B, Windows VST3, pluginval, FL Studio, Quick4 UI or production integration verified. Native algorithm/code and reference audio remain separate, no source/table copying.

Next: map Gem band residual routing and actual parameter/control provenance; inspect VCC table target processing stages and nonlinearity; AirEQ Earth/Air FIR coefficient setup; FG-401 detector gain law; TVB true-peak and delay modulation. Preserve decompiler-only scope and previous evidence.
