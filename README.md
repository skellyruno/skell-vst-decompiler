# Skell VST Decompiler 🩻

Private **read-only native binary DSP research** for Skelliere and the Skell audio ecosystem. This does not convert a commercial VST3 into recovered C++ source. It records an auditable trail from native instructions → mathematically supported operations → independently coded DSP experiments → audio A/B measurements.

## First milestone: real TVB compressor filter-bank recurrence

The supplied `TVB Rack V2.vst3` (SHA-256 `cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9`) contains a native compressor processing branch starting at RVA `0x5D07BF`. Eleven x64 instruction/address/operand checks confirm one **transposed direct-form II biquad** (`y=b0*x+z1`, `z1'=b1*x-a1*y+z2`, `z2'=b2*x-a2*y`). An additional structural check confirms **24 repeated sections** with five adjacent coefficients and two channel-specific state floats per section. The per-channel state stride is 192 bytes (`24 × 2 × 4`). See [`docs/TVB_COMPRESSOR_BIQUAD_24.md`](docs/TVB_COMPRESSOR_BIQUAD_24.md).

**Updated finding:** these are six groups of four in a detector branch, not a serial audio EQ. Cutoff/Q assignments remain unknown. Conventional gain computation and parts of the alternate modes are documented below. This is static analysis of native instructions, not measured TVB or VMR sound. A 24-section code motif does not establish a one-to-one mapping to TVB's 24 dynamic EQ controls.

### Confirmed compressor coefficient-setup math calls

In the TVB compressor's setup region RVA `0x5CFA7F–0x5D07BF`, direct-call target and import-thunk resolution confirms **16 calls to `expf`, 10 to `powf`, and 5 to `logf`**. These strongly suggest time constants, frequency/dB transforms, or nonlinear coefficient calculations; they do **not** recover the exact user-knob mappings or prove all calls are made on every preset. The paths are stored with RVAs in `reports/tvb_compressor_coefficient_math_calls.json`.

### Use it locally

Python ≥3.10; no runtime Python dependencies. `objdump` (GNU binutils) is required only for disassembly.

```bash
python -m unittest discover -s tests -v
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode inventory
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-biquad --out local/first_biquad.json
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-bank --out local/24_section_proof.json
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-compressor-setup --out local/coefficient_math_calls.json
python -m skell_vst_decompiler "FG-116.epl" --mode trace --rva 0x160540 --bytes 4096 --out local/fg116_trace.json
```

`--mode tvb-bank` deliberately **refuses to reuse the known offsets** if the binary SHA-256 differs. Every stage must pass explicit instruction checks. Generic `trace` returns bounded call targets and *candidate* read-only scalar constants, never claiming a function's meaning just because it contains floating-point arithmetic.

### Roadmap

1. Extend bounded call-graph tracing to x64 indirect virtual dispatch (without executing plugin code or touching license/activation protections).
2. Recover coefficient-construction dataflow (filter design and smoothing time constants), validate against controlled source build hashes and native instruction listings.
3. Compare authorized offline WAV renders at matched levels before implementing **original** antialiased Skelliere effects.
4. Preserve Skelliere VST3 identity, presets, automation IDs, slot type mappings and Tune latency; gate DSP changes behind explicit new modes.

All vendor binaries, decoded resources, extracted commercial code, licenses and private user audio stay **outside Git**. Source evidence under `docs/` contains only short arithmetic descriptions, addresses, public-format descriptions and analysis provenance. See [`AGENTS.md`](AGENTS.md).

## Dynamics equation index (new)

The conventional compressor target knee, attack/release recurrence, dual recovery, gain conversion, and six-group detector topology are now supported by exact-build native evidence. **Correction:** the earlier 24 filter motifs are six groups of four feeding six independent peak/power states, not one serial 24-stage audio EQ. Alternate gain-curve interpolation and static initialization are now verified; later runtime mutation remains unknown. [Full dynamics research](docs/TVB_DYNAMICS_EQUATIONS.md).

```bash
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-dynamics --out local/dynamics.json
python -m skell_vst_decompiler.catalog reports/tvb_dynamics_equations.json "gain reduction"
python -m skell_vst_decompiler.catalog reports/tvb_dynamics_equations.json 0x5d1b35
python -m skell_vst_decompiler "FG-116.epl" --mode dispatch --rva 0x6f740 --entries 7
```

The catalog can be searched offline by keyword or hexadecimal RVA. It includes region byte fingerprints, source file offsets, equation summaries, confidence and linked checkpoint/constant/call addresses. Generic dispatch inspection samples bounded static entries, not a live selector or a verified vendor audio algorithm. Never execute or patch vendor binaries. No runtime plugin tests are implied by static evidence.

## Alternate dynamics and function navigation

[New table-provenance and adaptive recovery report](docs/TVB_ALTERNATE_DYNAMICS.md). `--mode tvb-curves` verifies the exact build, both table initialization paths (459 finite points), curve row interpolation, mode-1 coupled recovery and mode-2 nonlinear attack/history release. It emits hashes and structural summaries, never original table arrays. `--mode function --rva 0x5d18d6` maps an address to its compiler unwind range; `--mode xref --rva 0x16a50 --bytes 337 --target 0x77e7a40 --target-bytes 616` locates a table initializer reference. Generic navigation also works with supplied VMR binaries. No vendor audio execution or complete algorithm parity is implied.
