# TVB limiter initialization evidence — 2026-11-24

## New native findings

The original TVB Rack V2 binary was recovered from the owner's private Library, SHA-256 matches the earlier exact build cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9. Read only, no execution or protection analysis. Prior rack-path report identified the three 12-tap dot products but not their initialization.

- 0x5dc801–0x5dc878: same byte flag at object offset 0x168 selects 0.1 ms (set) or 2 ms (clear). The selected duration is scaled by 0.001 and the setup sample-rate field; a large double bias followed by low-word read is consistent with nearest integer conversion under normal IEEE rounding. Signed nonnegative clamp and storage at 0x178. Previously verified delay reader consumes that field. Exact host latency reporting and UI control name remain unknown.
- 0x5dcc72–0x5dce88: bounded 3-row, 12-tap FIR construction, using standard Blackman-windowed sinc. The double center values in the tap coordinate are 5.75, 6.0, 6.25. The integer-center row is mathematically a near-impulse (floating arithmetic residuals possible). Double accumulator, float coefficient storage, guarded normalization by the pre-rounding coefficient sum. These are not three uniformly spaced *fractional* phases of a conventional four-times interpolator. Runtime read orientation, combined phase coverage and worst-case intersample error still require dedicated validation. No generated vendor coefficient arrays stored.
- 0x5dd1bd–0x5dd20c: the same flag selects 0.02 ms (set) or 0.4 ms (clear) for an exponential retention coefficient, with the rate stored at 0x170. This is coefficient timing, not measured total attack or output latency.
- 0x5ddd17–0x5ddde1: flag-controlled alternate dual reduction envelope with separate rise/fall retention, maximum of both states, versus single reduction smoothing with previous linear gain converted to dB. Complete release mapping and mode activation remain open.

## Reproducibility

Manually reviewed operand flow, 67 mnemonic checkpoints agreed between GNU objdump and LLVM objdump, 20 float/double scalar checks, four imported math calls resolved through PE import table. Four exact code-region hashes anchor the full instruction bytes, not just mnemonics. The new verifier ran twice against the actual private source with identical counts; four new unit tests passed. Archived Multi Engine Lab baseline plus the new tests: 72/72 passed after fixing a schema collision: the manifest is in a dedicated reports/limiter_setup subdirectory because the root report glob is reserved for equation-atlas schema. Current full branch CI is still unverified; the archive is older than current head. No binary, coefficient array, vendor source, or private recordings committed. No other repository changes in this focused research batch. No JUCE build required for static analysis; no DAW render, true-peak certification or complete limiter clone claim.

Run from repo root: python -m skell_vst_decompiler.tvb_limiter_setup "/private/path/TVB Rack V2.vst3"

Manifest: reports/limiter_setup/tvb_limiter_setup.json. Next: trace release coefficient mode selection and host parameter provenance, compare history tap orientation and phase coverage, then expand native analysis to delay feedback/timing and EQ mode routing. Keep research separate from production plugins.
