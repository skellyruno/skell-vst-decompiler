# Compressor coloration and host parameter binding

Source: exact supplied TVB Rack V2 Windows x64 VST3, SHA-256 `cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9`. Read-only static analysis. This report contains mathematical identities and structural evidence, not a vendor processor implementation or a plugin-render comparison. Raw vendor arrays are deliberately excluded.

## Post-gain coloration (84 instruction checkpoints, 10 linked references)

The sample path at `0x5d1d60` multiplies the audio sample by the computed gain. Numeric mode 1 and mode 2 then use distinct nonlinear and linear coloration paths before the existing dry/wet and output-gain operations at `0x5d1ee1`.

- **Mode 1** (`0x5d1e8a–0x5d1ee1`): asymmetric polynomial `max(floor, x + a*x*x + b*x*abs(x))`, followed by helper `0x5d2330`. The helper contains three serial double-precision DF2T sections, 15 coefficients per row, six double state variables per channel (48 bytes). The 720-byte read-only coefficient bank contains six rows. Preparation at `0x5cf350–0x5cf468` chooses the closest of 44.1, 48, 88.2, 96, 176.4 and 192 kHz by absolute distance, with strict comparisons keeping earlier entries at ties. The actual table is fingerprinted, not exported. All 18 constituent sections have poles inside the unit circle. This does not establish runtime stability of every path or the actual sound.
- **Mode 2** (`0x5d1d79–0x5d1e88`): asymmetric rational map `x + (a*x*x + b*x*abs(x))/(1 + abs(x)/c)`, followed by two double-precision DF2T-shaped sections, 32 bytes of state per channel. The first section has zero b2 and a2, so is first order. The second has b1=a1. Setup `0x5d29e6–0x5d2b46` reads the stored sample-rate-like double and constructs coefficients using imported `tan`, `pow`, `sin`, `pow`, and `cos`. The two nonlinear maps' small writable initial calibration records are fingerprinted; possible runtime changes are not ruled out.

The linear response calculation of the mode-1 filter cascade at its 48 kHz row gives approximately +0.289 dB at 20 Hz, -0.148 dB at 100 Hz, +0.007 dB at 1 kHz, -0.060 dB at 5 kHz, -0.607 dB at 10 kHz, -7.741 dB at 20 kHz. This is a calculation from local table coefficients, **not measured VST3 audio**. Filter attenuation does not prove antialiasing or oversampling; folding can occur before a filter. Other sample-rate row summaries are in the JSON report. No claim of parity with analog hardware or VMR.

## Host parameter chain (116 instruction checkpoints)

The parent constructor establishes an embedded rack object at parent+0x1e90 (`0x33c00d–0x33c014`). Its initializer constructs two `CompressorModule` objects at rack+0x324d8 and rack+0x33500 (`0x34bd12–0x34bd26`), hence parent offsets **0x34368 and 0x35390**. The compressor constructor sets the actual vtable at RVA 0x9273d0; its sixth slot points to the known processing prologue 0x5cfa50. This proves why a search for a bare displacement cannot identify a particular object. For example a separate effect also writes 0x18c/0x190; those writes are NOT evidence of compressor knob binding.

The 15 primary name-to-handle lookups at `0x340d06–0x340f31`, the 19 indexed secondary lookups at `0x33c52f–0x33c670`, and four additional lookups at `0x33c7e4–0x33c86f` were decoded from their original string references and destination pointer slots. The secondary list includes two slots for `comp2_on`. The processing function rooted at `0x342840` loads named handles, reads their float/flag values, applies range/default conditions, and writes to the two proven compressor instance bases. The catalog stores **25 checked read/dereference/store endpoints**, not a full symbolic control-flow reconstruction.

| Host parameter | Instance | DSP field | Meaning supported by prior DSP trace |
|---|---|---|---|
| comp_ratio | first | 0x154 | ratio |
| comp_knee_db | first | 0x158 | knee |
| comp_attack_ms | first | 0x15c | attack |
| comp_release_ms | first | 0x160 | release |
| comp_auto_release | first | 0x164 | recovery flag |
| comp_mix | first | 0x170 | blend |
| fx_comp_la2a_hifreq | first | 0x18c | detector control field (mode-dependent consumption) |
| comp2_threshold_db | second | 0x150 | threshold field |
| comp2_ratio / comp2_knee_db | second | 0x154 / 0x158 | ratio / knee |
| comp2_attack_ms / comp2_release_ms | second | 0x15c / 0x160 | timing fields |
| fx_comp2_la2a_limit | second | 0x188 | optical mode flag |
| fx_comp2_la2a_hifreq | second | 0x18c | six-bank detector interpolation |
| fx_comp2_compress | second | 0x190 | nonlinear gain-curve coordinate calibration |

Mode assignments at 0x343ea2 and 0x343ea9 write 1 to the first instance and 2 to the second, respectively; the preserved nonvolatile register definitions were checked. This establishes fixed numeric mode assignments in **this processing path**. It does not establish how all host routes select an instance, or claim the registered `fx_comp_algorithm` values directly control this path. The primary threshold, input and CLA output participate in a compound lookup/conditional calculation with outputs at 0x150, 0x174, and 0x17c. Their complete equations and GUI gesture-to-host normalization remain open. The secondary input/output identifiers are preserved exactly in JSON; do not silently swap their host names based on inferred DSP meaning.

## Reproduce

```
python -m skell_vst_decompiler 'TVB Rack V2.vst3' --mode tvb-color --out local/color.json
python -m skell_vst_decompiler 'TVB Rack V2.vst3' --mode tvb-parameters --out local/params.json
python -m skell_vst_decompiler.catalog reports/tvb_coloration.json 'coloration'
python -m skell_vst_decompiler.catalog reports/tvb_parameter_mapping.json 0x344176
python -m unittest discover -s tests -v
```

The new generic bounded SOS-summary helper validates finite normalized float64 coefficients, pole radii, frequency-domain response, and source hash without publishing the coefficient array. The name/slot decoder validates exact syntactic lookup patterns and rejects incomplete indexed tables. It is not a general decompiler or automatic interprocedural alias analysis.

## Original Skelliere design direction

Prototype separate optional color stages using independently chosen transfer curves, antialiasing strategies, and filters. Validate DC balance, harmonic spectra, high-frequency aliases, gain staging, block-size behavior, latency and CPU against matched real audio before integration. Use independently calibrated detector morphing and program memory rather than copying vendor tables. No production Skelliere source, presets, identity, UI, or Tune latency changed. No JUCE build or host test was needed for this static Python research change; VMR gain law remains unresolved.
