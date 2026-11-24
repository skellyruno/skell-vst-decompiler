# Alternate dynamics and native table provenance

Source: exact supplied TVB Rack V2 x64 binary, SHA-256 in `reports/tvb_curve_provenance.json`. Read-only native investigation, not an execution or a reconstruction of commercial source. Numeric mode identifiers are not confirmed UI labels.

## Table initialization (new evidence)

The earlier lookup-table analysis located destinations in the virtual-only part of `.data`; this pass identifies their initializers. Mode 1 startup at RVA `0x16a50` calls `0x5d2c70`, which copies five rows of 61 words from file-backed read-only RVA `0xa5ba80`. All 61 paired loads and stores and the 244-byte stride are checked. Startup copies 1220 bytes to `0x77e7cb0`. Mode 2 startup at `0x16af0` calls `0x5d31b0`, a straight-line initializer of 616 bytes (two 77-point rows). A deliberately restricted MOV-store decoder verifies complete, non-overlapping byte coverage and finite float32 values. Startup copies to `0x77e7a40`. The two initial table payloads are fingerprinted; **459 values verified locally**. Raw vendor values are not exported or committed. Subsequent runtime mutations have not been excluded.

Lookup origins are -12 and -70 respectively. Interpolation is endpoint-clamped along each row. Mode 1 additionally selects/blends across rows using anchors 4, 8, 12, 20; an alternate flag selects row 4 directly. These are numeric source facts, not verified UI mappings. The two mode-2 initial rows are monotonic with flat regions; mode-1 rows contain negative steps. This is one reason not to blindly fit a single textbook ratio to the alternate curves.

## Adaptive dynamics

Mode 1 (`0x5d14aa–0x5d15af`) has a nonlinear target involving exp and optional pow. The primary state Q (object offset 0x210) uses different rise/fall coefficients; release scales its coefficient by 1/(1+kH). Secondary state H (0x214) smooths a transformed log1p output and feeds back into the target and release. The log1pf direct IAT call is resolved. Absolute scaling and UI parameters remain unverified.

Mode 2 (`0x5d18d6–0x5d1a90`) is more than a fixed one-pole envelope. For a rising target C and prior reduction G, the native recurrence is consistent with:

`delta=C-G; Gnew=G+min(delta, A*(1-exp(-delta/B))*exp(-G/D))`

A, B, D are setup-dependent factors (positive valid values assumed). The first exponential uses expm1f for numerical precision; the second uses expf. The release branch computes a state-dependent duration using a power law and history, clamped to selected bounds. It applies `Gnew=G+min(1,step/tau)*(C-G)`; the release structure and unresolved coefficients are in the JSON report. Secondary history `Hnew=H+alpha*(0.05*Gnew-H)` is stored at 0xd4c; G at 0xd48 and 0x204. These are local instruction-derived relationships, not a complete implementation or proof of plugin parity. A separate independent Skelliere experiment can compare fixed one-pole recovery against a history-aware model using held-out music and vocal renders.

## Navigation upgrades

The `function` command reads PE exception-directory runtime function records; these ranges can represent unwind fragments rather than complete logical functions, and leaf functions may have no record. The TVB compressor processing region containing the above state writes is `0x5cfa7f–0x5d1fe3` (9572 bytes). The exact TVB binary has 34,461 validated records; eight selected VMR modules have 161,683 combined. Earlier VMR jump-table wrappers lack covering records; no attempt to infer the real DSP from their absence. `xref` scans decoded RIP-relative references and direct control-flow instructions in a bounded window; it does not claim complete register dataflow or indirect targets. This is enough to follow the initializer reference, and to find the enclosing region for each equation.

```bash
python -m skell_vst_decompiler 'TVB Rack V2.vst3' --mode tvb-curves --out local/curves.json
python -m skell_vst_decompiler 'TVB Rack V2.vst3' --mode function --rva 0x5d18d6
python -m skell_vst_decompiler 'TVB Rack V2.vst3' --mode xref --rva 0x16a50 --bytes 337 --target 0x77e7a40 --target-bytes 616
python -m skell_vst_decompiler.catalog reports/tvb_curve_provenance.json 'history'
python -m unittest discover -s tests -v
```

No original plugin execution, license changes, vendor table distribution, production Skelliere changes, JUCE build, sound-quality, CPU or latency claim. VMR's dynamics remain unresolved. No need for JUCE in this Python-only research tool. Next: map complete independent detector control scaling and evaluate measured real outputs.
