# Skell VST Decompiler 🩻

Private **read-only native binary DSP research** for Skelliere and the Skell audio ecosystem. This does not convert a commercial VST3 into recovered C++ source. It records an auditable trail from native instructions → mathematically supported operations → independently coded DSP experiments → audio A/B measurements.

## First milestone: real TVB compressor filter-bank recurrence

The supplied `TVB Rack V2.vst3` (SHA-256 `cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9`) contains a native compressor processing branch starting at RVA `0x5D07BF`. Eleven x64 instruction/address/operand checks confirm one **transposed direct-form II biquad** (`y=b0*x+z1`, `z1'=b1*x-a1*y+z2`, `z2'=b2*x-a2*y`). An additional structural check confirms **24 repeated sections** with five adjacent coefficients and two channel-specific state floats per section. The per-channel state stride is 192 bytes (`24 × 2 × 4`). See [`docs/TVB_COMPRESSOR_BIQUAD_24.md`](docs/TVB_COMPRESSOR_BIQUAD_24.md).

**Limits:** We have not proven whether all stages process the audible signal or the detector, nor recovered cutoff/Q assignments or a complete compressor gain computer. This is static analysis of native instructions, not measured TVB or VMR sound. A 24-section code motif does not establish a one-to-one mapping to TVB's 24 dynamic EQ controls.

### Use it locally

Python ≥3.10; no runtime Python dependencies. `objdump` (GNU binutils) is required only for disassembly.

```bash
python -m unittest discover -s tests -v
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode inventory
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-biquad --out local/first_biquad.json
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-bank --out local/24_section_proof.json
python -m skell_vst_decompiler "FG-116.epl" --mode trace --rva 0x160540 --bytes 4096 --out local/fg116_trace.json
```

`--mode tvb-bank` deliberately **refuses to reuse the known offsets** if the binary SHA-256 differs. Every stage must pass explicit instruction checks. Generic `trace` returns bounded call targets and *candidate* read-only scalar constants, never claiming a function's meaning just because it contains floating-point arithmetic.

### Roadmap

1. Extend bounded call-graph tracing to x64 indirect virtual dispatch (without executing plugin code or touching license/activation protections).
2. Recover coefficient-construction dataflow (filter design and smoothing time constants), validate against controlled source build hashes and native instruction listings.
3. Compare authorized offline WAV renders at matched levels before implementing **original** antialiased Skelliere effects.
4. Preserve Skelliere VST3 identity, presets, automation IDs, slot type mappings and Tune latency; gate DSP changes behind explicit new modes.

All vendor binaries, decoded resources, extracted commercial code, licenses and private user audio stay **outside Git**. Source evidence under `docs/` contains only short arithmetic descriptions, addresses, public-format descriptions and analysis provenance. See [`AGENTS.md`](AGENTS.md).
