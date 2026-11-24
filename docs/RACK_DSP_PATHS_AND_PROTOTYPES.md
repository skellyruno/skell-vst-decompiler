# Rack DSP paths and independent native experiments

## Static native evidence (exact input builds only)

`reports/tvb_rack_paths.json` checks 139 instructions in 10 local regions. `reports/vmr_effect_paths.json` checks 26 instructions across three effect candidates. Source fingerprints, half-open RVAs and code-range hashes are preserved; no original binary, executable code or raw coefficient arrays are distributed. Static candidates do not establish runtime dispatch or complete behavior.

### EQ

Eight-branch TPT coefficient builder at 0x5a5ef0, jump table 0x5a6118, mono sample consumer at 0x5a43e0. Standard state-variable relationships: g=tan(pi*f/Fs), k=1/max(Q,0.025), A=10^(gain_dB/40); frequency clamped to 1..0.49 Fs. Bell adjusts damping to k/A, low shelf adjusts g to g/sqrt(A), high shelf to g*sqrt(A). The core integrator coefficients are a1=1/(1+g*(g+k)), a2=g*a1, a3=g*a2 after these adjustments. Each response is a weighted mixture of input, bandpass and lowpass states. Verified branches cover highpass, bell, low shelf, high shelf, notch, bandpass, lowpass, allpass. These are familiar textbook filter structures; full host-control mapping and all routing modes remain unresolved.

### Limiter and gate

- Limiter regions 0x5dd820, 0x5ddbbe, 0x5de006: three 12-tap fractional-phase peak candidates, monotonic rolling peak queue, soft knee and delayed gain application with final sample clamp. With u=level-ceiling and h=half-knee width, middle branch reduction is (u+h)^2/(4h); outer branches are zero and u. Exact fractional-phase positions, true-peak certification, latency settings and full alternate envelope modes are not established.
- Gate regions 0x5c99ac, 0x5c9a47: first-order highpass detector, stereo-linked absolute peak, attack/release envelope, hysteresis with hold countdown and smoothed attenuation. Closed attenuation is bounded below by a floor. Full knob mapping unresolved.

### Spatial effects

Width (0x5d5f66): mid/side reconstruction with adjustable decorrelation. Delay (0x5d6a55): linear fractional history reads, two smoothing stages and selectable feedback routing. Reverb (0x5d8ba7): eight indexed modulated delay lanes, damping, optional bounded nonlinear coloration. Full delay/reverb coefficient mapping, feedback matrix and decay times remain unresolved.

### VMR

Six explicitly bounded table entries per module were examined. Slots 4 and 5 point to the same candidate in each of FG-116 (0x1619a0), FG-2A (0x156b20), FG-Stress (0x162790). FG-116 has a smoothed scalar gain multiplication; FG-2A has two double-precision first-order filter passes; FG-Stress has a linked peak detector P=max(p,p+a*(Pprev-p)). Runtime-selected slots, target gain laws and analog calibration remain unknown. No protection code inspected or modified.

## Original prototypes and genuine PCM experiment

`experiments/skelliere/OriginalDynamics.h` contains independently written sample-peak lookahead limiter and adaptive bell, with original time constants and no vendor coefficients. C++17 standalone render harness and native regression test require no JUCE. Offline 4x SciPy polyphase oversampling is **not** a real-time oversampler. No production Skelliere files are changed.

A privately supplied 44.1 kHz stereo music excerpt (60–72 seconds, chosen as the loudest 12-second nonoverlapping window) was rendered by the compiled native processor. +6 dB input drive for the limiter, -1 dBFS nominal ceiling, -1.25 dBFS internal ceiling in the offline oversampled variant. The already-hot dry input reaches 0 dBFS sample peak and +2.13 dBFS estimated intersample peak. All raw renders are float WAV, delay-aligned and unnormalized. Aggregate metrics only in Git; original audio, source hash and listening files stay private.

| Variant | Sample peak dBFS | Estimated 4x peak dBFS | RMS dBFS |
|---|---:|---:|---:|
| Sample-peak baseline | -1.000 | +1.133 | -5.946 |
| Native 3ms lookahead | -1.000 | +1.133 | -6.157 |
| Offline 4x lookahead + margin | -1.227 | -1.182 | -6.576 |

Dynamic bell reduced 150–400 Hz band RMS by 2.257 dB, maximum dynamic cut 4.949 dB; static -5 dB bell reduced band RMS by 2.674 dB. EQ can raise peaks despite cutting; downstream headroom needed. These are descriptive measurements, not subjective quality or certified true peak. Listening pair RMS-matched separately (+0.630 dB adjustment to candidate); not LUFS-matched and not used to assess peak ceiling. The oversampled experiment contains a safety margin and different gain, so the measured improvement is not attributable solely to oversampling. 132 samples native lookahead at 44.1 kHz; 529 at 176.4 kHz. No real-time oversampler latency, DAW/PDC, CPU or commercial plugin render verified.

```sh
g++ -std=c++17 -O2 -Wall -Wextra -Werror experiments/skelliere/render.cpp -o /tmp/skell_render
python experiments/render_original_rack.py /path/to/private.wav local/music --renderer /tmp/skell_render
python -m unittest discover -s tests -v
g++ -std=c++17 -O2 -Wall -Wextra -Werror experiments/skelliere/test_original.cpp -o /tmp/skell_tests && /tmp/skell_tests
```

Next: proper real-time oversampling and measured host latency/CPU, dry vocal/transient corpus with level-matched listening, optional compatibility-preserving integration only after verification. VMR full gain laws, vendor runtime modes and reference audio remain unverified.
