# Deep native DSP research and three independent engines — November 25, 2026

## Verified original binary evidence

Read-only local disassembly of five exact SHA-256 matched private files: Gem Dopamine-64.vst3, FG-401.epl, AirEQAir.epl, AirEQEarth.epl and VCC Channel.epl. Seven bounded code regions, 141 selected opcode checkpoints agreed between GNU objdump and LLVM objdump, with exact code-region SHA-256 hashes in `reports/native_scoped/deeper_engines_2026_11_25.json`. Count is instruction checkpoints, not distinct algorithms. No vendor executable was launched, and no code bytes, source dumps, license bypass, calibration coefficient arrays, private audio or source binaries are committed.

### Gem Dopamine — confirmed second-order IIR filter and routing

The helper at RVA 0x560150–0x560605 multiplies five signals: current and two preceding input samples, plus two preceding output samples. At 0x5605ea–0x560602, the final two input samples from r8 and final two output samples from r9 are stored in four persistent fields. This confirms the local second-order IIR (biquad) recurrence:

`y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] + c1*y[n-1] + c2*y[n-2]`.

The c coefficients already include their signs. This corrects the earlier inconclusive “five-term filter” label. Filter coefficient setup, modes, cutoff, host knob identity and actual de-esser topology are not established. The containing candidate path at RVA 0x58bbe0–0x58bef5 calls the filter helper three times with separate object offsets, followed by four calls into an envelope-dependent nonlinear path. RVA 0x58c100–0x58c49b processes 32 values in four loop iterations of eight samples, selecting distinct squared rising and linear falling corrections. Local scalar references include 110, 10, 0.01 and 0.08. These are observed arithmetic clues, not enough to identify exact excitation or de-esser algorithms.

### VMR engine findings

- **FG-401**: RVA 0x15e050–0x15e19c has an input-versus-previous-state comparison and two retention coefficients with double-precision persistent updates. This confirms direction-sensitive smoothing used by candidate processors, not a complete gain computer.
- **AirEQ Air**: RVA 0x246e80–0x247027 has a 64-slot double-precision circular FIR history; the cursor wraps with a mask 0x3f. Both branches of the ring dot-product sum current plus remaining 63 historical contributions. Weights, phase response, latency, coefficient initialization and whether other modes use the FIR remain unresolved.
- **AirEQ Earth**: RVA 0x145340–0x14557f indexes two separate groups of three indirect calls using boolean/mode-derived selectors. This is a real multistage dispatch topology, not a recovered filter equation.
- **VCC Channel**: RVA 0x176970–0x176b4f is better classified as stateful gain interpolation / buffer ramp, NOT yet the actual saturation/coloration core. This corrects an earlier suspected color core; keep the actual nonlinear path unresolved.

## Independently written Skell DSP engines — research only

Source `experiments/engine_lab/IndependentEngines.h`, standalone tests `experiments/engine_lab/test_engines.cpp`. These are original candidate DSP designs, **not** vendor algorithms or vendor-compatible implementations.

1. `PresenceEngine`: 4th-order Linkwitz–Riley high/low crossover built from Butterworth biquads, stereo-linked high-band detector, adjustable dynamic brightness/threshold/amount, smoothed high-band gain and mix. At unity the split has approximately flat magnitude, not sample-for-sample dry identity; mix=0 bypasses exactly.
2. `ProgramLeveler`: independent stereo-linked adaptive release with activity memory blending two exponential release poles, ratio-based gain reduction, separate gain smoothing, makeup and wet mix. No vendor-specific transfer law claimed.
3. `ColorEngine`: independently designed asymmetric `tanh` saturation, DC blocker, drive/bias/output/mix. **No oversampling**: high-frequency aliasing must be measured and reduced before production use.

`prepare` computes constants; `process` has no dynamic allocations, locks, or I/O in the supplied source. Sample rates 44.1/48/96/192 kHz passed g++ C++17 optimized -O3 -Wall -Wextra -Werror and separate address/undefined sanitizer builds. LR4 magnitude sum within 0.08 dB at 100, 1000, 2200, 5000 Hz; zero-mix identity, deterministic reset, linked stereo, unity ratio, impulse stability, nonfinite values and harmonic response were checked. Synthetic 48 kHz 1 kHz stimulus generated a 2 kHz harmonic at linear amplitude 0.0055821 with asymmetric color versus below 0.0000001 when symmetric. This is not a vendor or subjective comparison.

Representative local Linux optimized timing with input generation outside the timed loop, expressed per **48 stereo samples** at 48 kHz: Presence approximately 0.99 µs, ProgramLeveler 1.16 µs, Color 0.79 µs. Values are machine/compiler-specific research results, NOT host/VST3 CPU or release measurements. ASan results were slower as expected. No explicit lookahead/delay buffers, but filters add frequency-dependent phase response.

Reproduce:
```sh
g++ -std=c++17 -O3 -Wall -Wextra -Werror experiments/engine_lab/test_engines.cpp -o /tmp/skell_engines
/tmp/skell_engines
g++ -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Werror experiments/engine_lab/test_engines.cpp -o /tmp/skell_engines_san
/tmp/skell_engines_san
python -m unittest discover -s tests -q
```

Local archived project plus new evidence tests: 79/79 passed. The archive is older than the latest GitHub head; full exact-branch CI is a separate gate. Previous branch head abb8f87 passed all eight CI workflows. New exact-head CI pending. No Quick4 UI, real vocal/music A/B, FL Studio host, pluginval, Windows VST3 or production changes claimed.

Next research: trace Gem biquad coefficient stores and UI mapping, FG-401 detector/gain computer, AirEQ mode-specific coefficient generation, actual VCC nonlinear process, and TVB missing modulation; next independent engine quality gate is 2x/4x oversampling with measured alias/phase/CPU tradeoffs and real authorized music A/B. Preserve all previous evidence and stay in decompiler repo only.
