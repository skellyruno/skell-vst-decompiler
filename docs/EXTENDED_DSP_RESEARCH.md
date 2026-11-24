# Extended DSP research: gain staging, dynamic EQ, de-essing, VMR utilities

## Evidence and limits

This pass uses the supplied Windows PE images read-only, TVB SHA-256 `cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9`, and FG-116, FG-2A, FG-Stress extracted from the reconstructed original VMR ZIP (SHA-256 `353f23373ac05d7b2121c313073f08c708e879d839115d4ce5d30657732f481e`). Neither vendor executable was run. The exact-build verification rejects other source hashes. Local mathematical identities describe one native path for finite valid input, not complete recovered source code, license circumvention, or audio equivalence. No raw calibration arrays or original binaries are exported.

## Compound compressor gain staging

At 0x342fa8–0x3431c3, primary threshold and CLA output values index two 60-point float32 curves at 0x928270 and 0x928360. Both use coordinate clamp(value+59,0,59), integer index capped at 58 and fractional linear interpolation. For the verified primary path, let z = input_curve(host_threshold) + host_input_db, I = clamp(z,-12,24), e = z-I, T = clamp(-e,-72,0), O = clamp(output_curve(host_CLA_output) + host_output_db + e,-120,24). If either host threshold or CLA output is at or below the native -59.95 sentinel, O is -120. Missing CLA output defaults to -18. The path writes I/T/O into fields 0x17c/0x150/0x174 respectively and zeroes manual and automatic makeup fields. The final ratio is bounded separately. The two curve fingerprints are recorded, not their values. This explains the nontrivial mapping of drive versus threshold. It does not prove GUI normalization or other routing paths.

At 0x5d052e–0x5d07b5, field 0x17c is converted via 10^(dB/20) (zero at or below -100 dB), smoothed, and applied to input samples. Field 0x174 follows an independent smoothed output gain path. At 0x5d1ee1–0x5d1f25 the final blend is output_gain*((1-mix)*saved_dry + mix*colored_wet) when the mix branch is active. The reduction-to-linear conversion and other mode-specific wet gain multipliers are not all linked back to the complete host automation routes.

## Dynamic EQ

At 0x35bb80–0x35bc6c, the suite processes chunks of at most 32 samples, calls detector routine 0x5a5090, transfers 24 signed gain adjustments with setter 0x5a3d90, then calls audio EQ 0x5a3dd0. The detector records have 0x168-byte stride. The bandpass branch computes g=tan(pi*f/Fs) with f clamped to [1,0.49*Fs], k=1/max(Q,0.025), a1=1/(1+g*(g+k)), a2=g*a1, a3=g*a2. The two-state TPT recurrence uses bandpass output k*v1. Other routing/filter branches also exist. Two absolute-envelope states use fast attack/release and slow smoothing; slow retention is exp(-1/(2*Fs)). At 0x5a5bfc–0x5a5cbf, signed gain adjustment is range*clamp((L-T)/K,0,1), where K=clamp(6+0.5*abs(range),6,24). Threshold is either a fixed field or slow detector level plus 3 dB. Disabled/near-zero-range bands produce zero adjustment. No complete parameter-name-to-field map, audio filter-mode reconstruction, or dynamic EQ host render is claimed.

## De-esser

At 0x5d3c5e–0x5d3dfd, detector cutoff is clamp(field0x150 * mode_scale,2000,12000), mode_scale selected from {1.3,1,0.75}. The crossover helper at 0x5b6b20 implements two TPT lowpass sections with shared g and k; low=LP2(LP1(x)), high=HP1+LP1-k*BP1-low. Their sum is an allpass, not necessarily sample-identical dry. The native detector at 0x5d3e44 takes the maximum absolute high band over channels, with exponential attack/release retention for 0.12 ms and 28 ms. The state converts to dB with -120 dB floor. For excess u=L-threshold and positive ratio R, target reduction is min(cap,(1-1/R)*u*(1+0.55*clamp(u/8,0,1))) above threshold, zero otherwise. An independent gain envelope uses adjustable millisecond fields 0x16c/0x170. The gain is 10^(-GR/20), with a zero cutoff at -100 dB. Wideband mode multiplies high+low by gain, split-band mode multiplies only high before adding low; a flag excludes the low component. Host labels and all valid parameter ranges are not established. Evidence locations and constant checks are in reports/tvb_extended_dsp.json.

## VMR advancement: remove false DSP candidates

The sampled slot-0 dispatchers in all three native modules are now classified by instructions, not names. The dispatcher at 0x6f740 reaches an 8-byte-element buffer copy (scalar byte moves and 16-byte vector moves). FG-116 and FG-2A dispatchers at 0x6f780/0x6f7a0 reach float32-to-float64 and clamped float64-to-float32 conversion kernels. In FG-Stress the corresponding conversions are at 0x6f7a0/0x6f7c0. This is nine classified utility paths, not nine effect-specific algorithms. FG-Stress processor vtable 0xe9f848 slot 8 points to wrapper 0x160a30: 32-frame chunk setup, copy calls, and indirect calls 0x160b96 and 0x160c25. The exact processing target is unresolved; no oversampling-factor or compressor-gain claim follows from these utility paths. This corrects any earlier interpretation that these dispatchers themselves were the gain computer.

## Actual PCM measurement (independent model, not vendor output)

The environment is Linux and supplied binaries are Windows PE32+; no compatible licensed Windows host or FL Studio session is available. Actual TVB/VMR audio renders remain blocked. The optional WAV analyzer reads integer PCM and float WAV, uses a coherent one-second FFT, measures fundamental, peak, RMS, DC and harmonics/folded-bin candidate power, and excludes ambiguous collisions through order 15. It cannot uniquely attribute noise or higher-order collisions; a missing bin family is null rather than a fictitious measurement. An independent asymmetric soft-saturation candidate with an original bias and gain plus 15 Hz DC blocking was rendered to float WAV at 1x and 4x, using offline polyphase resampling. Not a real-time CPU/latency benchmark, not the vendor equation, no parity or quality claim. See reports/original_color_summary.json and the separate WAV package. At -6.02 dBFS input, 17 kHz / 48 kHz folded candidate power is -17.79 dBc (1x) versus -76.88 dBc (4x), and 31 kHz / 96 kHz is -17.79 versus -84.60 dBc. At 1 kHz / 48 kHz, harmonic power through order 15 is -17.79 dBc in both cases. These are actual generated PCM measurements, not real plugin render measurements.

For licensed DAW verification: use the supplied original dry WAVs, set a specific isolated effect, disable unrelated effects, record exact parameter values/version/rate/buffer and use 32-bit float exports with no normalization, dither, or sample-rate conversion. Retain a full second of settled coherent tone after at least one second of preroll. For each reference render use `python -m skell_vst_decompiler.audio_probe wet.wav --tone 17000 --source "actual DAW render, effect and settings recorded"`. The source label is user-declared, not authenticated by the analyzer. Repeat for bypass, low/medium/high drive, matched gain, 48/96 kHz; use previously supplied level-step/transient/stereo tests and actual vocals for recovery and sound comparison. Do not run untrusted binaries or bypass licenses.

## Reproduction

```
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-extended --out local/extended.json
python -m skell_vst_decompiler "FG-Stress.epl" --mode vmr-utilities
python -m skell_vst_decompiler.catalog reports/tvb_extended_dsp.json "de-esser"
python -m pip install -e '.[audio]'
python -m experiments.render_original_color local/audio
python -m unittest discover -s tests -v
```

Local tests passed 41/41; the real-binary verification passed 115 instruction checks across nine regions, 21 scalar checks and linked math calls, plus nine VMR utility paths and the FG-Stress wrapper. This research-only change does not alter Skelliere production DSP, parameters, artwork or latency. JUCE is not locally installed and not required for Python research; no JUCE build was attempted. Real plugin/DAW audio, exact VMR gain equations, CPU and latency remain unverified.
