# Detector morphing and coefficient provenance

Source: the SHA-256-verified original TVB Rack V2 x64 executable. This is static evidence, not a vendor processor implementation or proof of audio parity.

## Newly established links

- Native field `0x18c` selects adjacent detector banks at six anchors (0, 20, 40, 60, 80, 100). The index and interpolation fraction are saved in stack locations used by the detector loop. For valid inputs the fraction is linear within each interval. The out-of-domain branch above 100 resets the selection to index 0/weight 0; do not assume arbitrary input is clamped.
- Native field `0x190` is clamped to 0..100 and mapped through a five-point decreasing calibration curve at coordinates 0,36,50,75,100. This is an offset subtracted before lookup into the existing 77-point gain curves. The calibration payload is fingerprinted rather than exported.
- In each adjacent bank, positive peak and power states are converted to logarithmic units. Power is doubled before log conversion (a +3.0103 dB shift). The code then blends peak and power in dB, blends adjacent bank levels, and subtracts 3.0103 dB and the calibrated offset before calculating the table coordinate. Peak and power level floors are -90 dB (the doubled power conversion uses -180 before halving). Exact silent/invalid-input behavior is not claimed by the positive-envelope equation.
- Two adjacent 56-byte calibration records are file-backed in writable `.data`. They supply attack shape/scaling, adaptive recovery, and detector blend settings; their initial values are all finite. Runtime changes to these records are not ruled out. Raw vendor arrays are not published.
- Setup computes a rate-dependent step of `1000/F` from the double at object field `0x198`, three exponentials for peak decay and one-pole updates, and the scale/reciprocal terms consumed by nonlinear attack. `F` is interpreted as sample rate, not yet confirmed by host execution. The exact five stack writes/consumers used for attack, release, and history were checked. This links the earlier isolated recurrences to setup rather than leaving their coefficients entirely unexplained.

The source verifier checks 67 instruction checkpoints, 19 linked address references, 18 scalar constants, the double timebase numerator, both calibration fingerprints and seven imported math calls. The original supplied frontend metadata separately labels the two intended alternate modes 1176-style and LA-2A-style. Their default numeric values are 1 and 2. The native registration path also contains the corresponding parameter identifiers, but a complete host setter-to-object-field trace is not yet established; do not rename fields 0x18c and 0x190 as confirmed UI controls.

## Reproduce

```
python -m skell_vst_decompiler 'TVB Rack V2.vst3' --mode tvb-detector --out local/detector.json
python -m skell_vst_decompiler 'TVB Rack V2.vst3' --mode fieldrefs --rva 0x5cfa7f --bytes 0x2564 --base rbp --offset=-0x50
python -m skell_vst_decompiler.catalog reports/tvb_detector_mapping.json 'detector selection'
```

`fieldrefs` indexes literal base+displacement operands, including signed stack offsets and indexed addressing. Its access labels are syntactic; it does not prove register aliasing, object identity, or which branch executes. On the exact TVB range the query above returns the setup write and adaptive release read of the same literal stack slot.

Independent design direction: try a smooth detector crossfade and separate time-constant calibration in a new Skelliere experiment. Tune independently using audio, rather than copying vendor tables. No production DSP, VMR algorithm reconstruction, JUCE/editor build or host audio validation in this pass.
