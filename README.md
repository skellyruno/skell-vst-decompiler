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

## Detector mapping and literal field navigation

[Detector morphing and coefficient provenance](docs/TVB_DETECTOR_MAPPING.md) connects the six detector groups to continuous neighboring-bank interpolation, dB peak/power blending, nonlinear control calibration and rate-dependent setup. `--mode tvb-detector` verifies the original build and emits calibration fingerprints, not vendor arrays. `--mode fieldrefs --rva 0x5cfa7f --bytes 0x2564 --base rbp --offset=-0x50` identifies literal memory-operand locations with conservative access labels. This works on bounded code windows in other PE binaries too; it is not full register alias analysis. Hexadecimal byte lengths are now accepted.

## Post-gain coloration and verified host binding

[Coloration and parameter-binding report](docs/TVB_COLORATION_AND_PARAMETERS.md). The exact-build `--mode tvb-color` verifies distinct FET/optical post-gain nonlinear paths, three vs two filter stages, and six nearest-rate FET coefficient rows. `--mode tvb-parameters` follows the parent/child constructor chain, validates named pointer lookup slots and maps 25 source/destination endpoints to two proven compressor instances. The reports record confidence, RVAs and aggregate filter-only math; no raw vendor tables or executable code are published. Real audio equivalence, the full compound threshold/input/output conversion and alternate host routes remain unverified.

## Extended DSP research and actual PCM analysis

[Compound gain / dynamic EQ / de-esser / VMR utility-path report](docs/EXTENDED_DSP_RESEARCH.md). `--mode tvb-extended` verifies the exact source build and indexes the nine native code regions; `--mode vmr-utilities` verifies the known FG-116, FG-2A and FG-Stress copy/conversion paths, not their compression algorithms. `python -m skell_vst_decompiler.catalog reports/tvb_extended_dsp.json 0x34308c` searches the new report by RVA. Install `.[audio]` for `python -m skell_vst_decompiler.audio_probe wet.wav --tone 17000`; the analyzer operates only on PCM exports, never loads commercial binaries. `python -m experiments.render_original_color local/audio` renders our independent nonlinear experiment. Actual vendor audio requires a compatible licensed DAW and remains unverified. No third-party coefficient arrays or binaries are published.

## Rack DSP paths and independent native music prototypes

[New rack DSP evidence and private music experiment](docs/RACK_DSP_PATHS_AND_PROTOTYPES.md). Exact-build `--mode tvb-rack-paths` checks ten local EQ/gate/limiter/spatial regions. `--mode vmr-effect-paths` verifies bounded dispatch slots and three local effect-specific candidates, not live runtime selection. The original standalone C++ adaptive bell and lookahead limiter live in `experiments/skelliere/`; they are not installed plugin modules. The music harness renders private local WAVs with delay alignment and computes estimated intersample peaks, band energy and RMS, plus separate RMS-matched listening files. Offline 4x resampling is not a real-time oversampling implementation. Only aggregate metrics are checked in; vendor binaries and user audio stay local. See the linked report for reproduction commands and limitations.

```sh
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-rack-paths --find limiter
python -m skell_vst_decompiler "FG-116.epl" --mode vmr-effect-paths
```

## Targeted Ghidra and reverb research

[Towel-Decomp](https://github.com/towelWet/Towel-Decomp) was reviewed. Its Ghidra workflow inspired our own optional, address-targeted headless bridge; no upstream files are copied. See [Ghidra / reverb workflow](docs/GHIDRA_REVERB_RESEARCH.md). Search across all equation reports, select exact-fingerprint RVAs, create a dry-run plan, and optionally export local C-like pseudocode and caller/callee candidates using an installed official Ghidra. Generated analysis stays in ignored local folders. The bridge's mock subprocess tests pass; actual Ghidra execution and Java script compilation are unverified until an installed runtime is available.

The exact-build TVB reverb verifier now checks 191 instructions across ten regions, including eight-lane Householder feedback, per-lane decay scaling, input-linked wet ducking and normalized output color. No vendor tables/code or runtime audio parity claims. Use `--mode tvb-reverb` and `python -m skell_vst_decompiler.research_index reports reverb`.

## VMR control-stream research and original spatial experiment

See [VMR control and spatial DSP](docs/VMR_CONTROL_AND_ORIGINAL_SPACE.md) for exact-build VMR local arithmetic (FG-116 gain slew and minimum envelope, FG-2A dual gain ramps and vector sum, FG-Stress bounded control streams), 92 checkpoints, and a separately authored Hadamard FDN with private music/impulse measurements. Run `python -m skell_vst_decompiler.vmr_control /private/path/FG-2A.epl` or search `reports/vmr_control_streams.json` through the existing catalog. Runtime compressor laws remain unresolved.

A separate real Ghidra smoke workflow uses the official pinned release and a compiled owned PE fixture; no vendor plugin is run or uploaded. The original spatial prototype lives under `experiments/skelliere/`; it is not installed in Skelliere Rack. Compile `test_space.cpp` and `render_space.cpp` with a C++17 compiler and run `python experiments/render_original_space.py /private/music.wav /private/output --renderer /path/to/render_space`. Keep audio and pseudocode out of Git.

## VMR nonlinear DSP and consolidated equation atlas

See [VMR nonlinear evidence](docs/VMR_NONLINEAR_ATLAS.md) for the verified clamped and variable-state FG-116 relationships, FG-2A biased curve / even-power polynomial candidate / post-polynomial filter, and FG-Stress three-region curve. Run `python -m skell_vst_decompiler.vmr_nonlinear /private/path/FG-2A.epl` to recheck the exact source fingerprint and instruction operands. The consolidated [DSP equation and code-location atlas](docs/DSP_EQUATION_ATLAS.md) contains 95 local evidence records; regenerate it with `python -m skell_vst_decompiler.evidence_book reports > docs/DSP_EQUATION_ATLAS.md`, or use `--format json`. Static calls and overlapping evidence windows are not counts of complete algorithms. Ghidra's previous real owned-fixture CI smoke passed, but vendor binary pseudocode and commercial audio parity are still unverified. No vendor source or processor implementation exported.

### FG-2A coefficient provenance

`python -m skell_vst_decompiler.vmr_coefficients /private/FG-2A.epl` verifies nine polynomial weight initializer/read endpoints, scalar rational helper candidates, and local branch merging. See [coverage and limitations](docs/FG2A_COEFFICIENT_PROVENANCE.md). The 9/9 scoped coverage is not a whole-plugin completion percentage.

### FG-2A filter / feedback provenance

Use `python -m skell_vst_decompiler.vmr_filter_provenance /private/FG-2A.epl` for fingerprint-gated verification of six filter setup records, 30 active coefficient fields, 60 channel read endpoints and 17 nonlinear feedback setup writes. See [filter and feedback provenance](docs/FG2A_FILTER_FEEDBACK_PROVENANCE.md). The consolidated atlas has 128 evidence regions; the counts are scoped static relationships, not an estimate of whole-plugin recovery. Generator internals, rational parameter initialization, live dispatch, full gain law and commercial audio are unresolved.
