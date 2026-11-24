# Native dynamics: verified equations and code-location index

## Provenance and scope

Source: original user-supplied TVB Rack V2 Windows x64 VST3, SHA-256 `cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9`. Read-only inspection with GNU objdump and PE data reads. The verifier rejects a different fingerprint, checks **119 opcode/operand checkpoints, 17 scalar constants and their code uses, two bit masks, 11 imported math calls**, and checks the six filter groups and six pairs of envelope states. The report's region SHA-256 fingerprints and file offsets permit a repeat audit without publishing raw vendor code. `instruction-verified` denotes a local mathematical identity for valid finite inputs; it does NOT imply the entire effect, UI mapping, sound, or exact IEEE rounding is recovered. `instruction-verified-structure` describes an identified topology or interpolation; `partial` denotes incomplete equations.

## Conventional native compressor branch (numeric mode 0)

At `0x5D07A0–0x5D07B5` the current input gain is multiplied into each channel sample and stored. At `0x5D1246–0x5D1266` the detector takes a maximum of absolute channel samples after optional detector filtering. A shared peak state at object field `0x200` tracks rising peaks instantly and falls toward the current detector level with a one-pole recurrence. At `0x5D128E–0x5D12EF`, this level is converted with `log10f`, scaled by 20, and floored at -90 dB. Mode 0 setup uses a 15 ms detector fall constant. The numeric selector is not equated to an unverified UI label.

Let `L` be detector dB, `T` threshold (mode 0 clamps the field at object offset `0x150` to -72..0), `R` ratio (field `0x154`), and `K` knee (field `0x158`). For valid positive ratio, `u=L-T`, `s=1-1/R`. At `0x5D1B2C–0x5D1BAC`:

- If `K <= 0.001`, target gain reduction is `s*max(0,u)`.
- For larger positive K, target is zero for `u<=-K/2`, `s*(u+K/2)^2/(2*K)` in the knee, and `s*u` above `K/2`.
- A standalone helper at `0x5D3130` repeats the same algebraic motif. Its caller relationships have not been established.

At `0x5D1C1B–0x5D1C52`, the single gain-reduction state at `0x204` follows the target using `g_new=g_old+a*(target-g_old)`; the coefficient changes for increasing vs decreasing reduction. Setup at `0x5D03A5–0x5D04F2` constructs one-pole coefficients with `expf`. Time helper at `0x5D22E0` establishes `a=1-exp(-1/(0.001*t*F))`, where t is a millisecond-style argument and F the second rate argument. The setup loads a sample-rate-like double from object `0x198`; runtime parameter mapping/units are not independently host-confirmed.

## Dual recovery option

At `0x5D1BAC–0x5D1C1B` the flag selects two separate dB states `0x208` and `0x20C` and returns their maximum. The first uses the ordinary attack coefficient and an auxiliary release coefficient based on `0.08*F`. The second uses coefficients based on `0.30*F` (rise) and `1.50*F` (fall), corresponding to 80, 300 and 1500 ms if F is sample rate. All three time constants are linked to the setup instructions and confirmed binary floats. Short and sustained events consequently can have different recovery in this branch; actual audio and control selection remain unmeasured.

At `0x5D1C9A–0x5D1CD9`, the code negates the dB reduction, checks -100 dB, and computes `powf(10,-0.05*g)` above that cutoff, zero otherwise; two more gain factors follow. A later optional mix operation (`0x5D1EE1`) combines dry-buffer and processed samples with complementary weights before multiplying by output gain. Exact makeup mapping, special modes and external host state still need verification.

## Correction to prior 24-section finding: six detector groups, not a serial 24-stage audio EQ

The mode-2 filter branch begins at `0x5D07BF`. Six groups each start from the same gain-adjusted input in `xmm7`, contain four five-coefficient/two-state filter motifs, and take a weighted absolute maximum across channels. Group weights are `0x700..0x714`. The groups feed six peak states `0xD18..0xD2C` and six power states `0xD30..0xD44` (code `0x5D15BE–0x5D172E`). Each peak is `P_new=max(d*P_old,p)`, and each power state is `E_new=E_old+a*(p*p-E_old)`. The following code (`0x5D172E–0x5D17BF`) reads indexed peak and power values, converts to logarithmic units, and blends them with complementary weights. This establishes a frequency-selective detector bank, not a 24-band audio EQ or proof of six particular frequency cutoffs. The compiler pipelines some coefficient multiplication across neighboring group boundaries; the verifier permits a bounded overlap, not an arbitrary search across the function.

Mode 1 uses a helper at `0x5D30B0` that interpolates an indexed 61-point curve (244-byte row stride). Mode 2 code at `0x5D1833–0x5D18D6` interpolates a 77-point curve (308-byte stride). For positive interior coordinate u, `i=floor(u)`, result `C[i]+(u-i)*(C[i+1]-C[i])`; endpoints clamp. These table **shapes and interpolation** are established. Their data base RVAs are not file-backed in this supplied build, and runtime initialization and full analog gain laws have not been reconstructed. No table values or original implementation are redistributed.

## VMR navigation progress

The two supplied modules FG-116 and FG-2A both have a three-instruction indexed jump-table pattern at RVAs `0x6F740`, `0x6F780`, `0x6F7A0`. The generic tracer examined seven candidate table entries each (42 total, all file-backed executable targets). Some slots are aliases. Runtime selector storage is not file-backed in both binaries. The sampled count is **not** proof of table extent, number of CPU modes, active branch, or effect algorithm. Native wrapper calls may simply be shared optimized buffer operations. Exact VMR dynamics and active oversampling remain unknown. See `reports/vmr_dispatch_catalog.json`.

## Independent mathematical validation (not a vendor render)

Unit tests confirm textbook quadratic-knee continuity and slope, a 12 dB excess at 4:1 producing 9 dB reduction and 0.354813 linear gain, one-pole recovery at 44.1/48/96/192 kHz, and a generic two-envelope model's different response to short versus sustained targets. No vendor executable was run. These tests verify math and analysis-tool behavior, not plugin parity, audio quality or CPU/latency.

## Reproduce and find code

```
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-dynamics --out local/tvb_dynamics.json
python -m skell_vst_decompiler.catalog reports/tvb_dynamics_equations.json "gain reduction"
python -m skell_vst_decompiler.catalog reports/tvb_dynamics_equations.json 0x5d1b35
python -m skell_vst_decompiler "FG-116.epl" --mode dispatch --rva 0x6f740 --entries 7
python -m unittest discover -s tests -v
```

The catalog lists code RVAs, file offsets, region fingerprints, confidence, equation summaries, checkpoint addresses, constants and math callsites. Searches work from the checked-in evidence without requiring the original binary. Static RVAs are build-specific and should never be reused with another hash.

## Skelliere design implications

Implement independent, separately selected experiments: a two-envelope recovery stage using our own tuned time constants, frequency-selective detection (start with one independently designed filter, expand only if useful), and optionally peak/power interpolation. Compare held-out real vocal and drum renders, gain-reduction curves, envelope timing, transient preservation, CPU, latency and automation before integrating. Preserve all existing states, plugin IDs and presets. No Skelliere production DSP changed in this investigation.
