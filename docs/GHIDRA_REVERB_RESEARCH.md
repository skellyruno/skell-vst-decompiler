# Targeted Ghidra backend and TVB reverb analysis

## Upstream assessment and provenance

[Towel-Decomp](https://github.com/towelWet/Towel-Decomp), tree `0162fb32883dcbee78e96cd3e045181d14c03553`, was inspected (`tdc.py`, `DecompileAll.java`, `README.md`). It wraps Ghidra headless analysis in Tkinter and exports all functions into one text file. The user stated permission to reuse it; no license was declared in the upstream tree. We retained the general workflow rather than copying its code: the original Skell bridge targets evidence addresses, uses a fresh private project per invocation, bounds analysis time and output, validates SHA-256, requires completion markers, and separates individual pseudocode files and caller/callee links. Towel-Decomp's GUI is not required. Ghidra must be installed from its official distribution. API reference: https://ghidra.re/ghidra_docs/api/ghidra/app/util/headless/HeadlessScript.html and https://ghidra.re/ghidra_docs/api/ghidra/app/decompiler/DecompInterface.html.

**Verification limit:** no Ghidra installation or usable download in this environment. The bridge's Python planning, CLI, manifests and subprocess orchestration were exercised using synthetic test fixtures, not Ghidra. Java exporter checked against the documented API but not compiled or run against Ghidra. A real smoke test on an owned binary is required before relying on its output. Never execute plugin binaries, bypass protections, commit vendor pseudocode or confuse decompiled C-like output with original source. Ghidra-inferred call relationships do not resolve arbitrary indirect calls. The exporter bounds each direction to 128 local addresses; that list is not necessarily exhaustive.

## Workflow (Windows/Linux, Python 3.10+)

Install official Ghidra and its required JDK. Run from the repository root. For Windows use PowerShell and your actual local paths. The following first command needs neither Ghidra nor the original binary:

```sh
python -m skell_vst_decompiler.research_index reports "ducking"
python -m skell_vst_decompiler.research_index reports --rva 0x5d92e8
python -m skell_vst_decompiler.ghidra_bridge "TVB Rack V2.vst3" --catalog-dir reports --query reverb
python -m skell_vst_decompiler.ghidra_bridge "TVB Rack V2.vst3" --catalog-dir reports --query reverb --ghidra-home "C:/RE/ghidra" --work-root local/ghidra
python -m skell_vst_decompiler.ghidra_bridge "FG-Stress.epl" --catalog-dir reports --query effect_candidate --ghidra-home "C:/RE/ghidra"
```

Omit `--ghidra-home` for a plan only. `--rva 0x...` can be repeated to choose individual addresses. At most 64 distinct requested addresses per run. `--seconds` controls the initial analysis timeout. The same function may cover several selected evidence regions, and is exported once. The output directory contains the plan, analyzer log, result manifest, call relationship manifest and private per-function pseudocode. Check both target and unique function counts. Keep it under ignored `local/` and out of source control. The exact build must match selected reports; reports for other builds are filtered, not blindly reused. On a first real run, inspect the log for importer errors and partial targets. No automatic execution or upload of generated code.

The combined index contains 67 region records (64 TVB, one each FG-116/FG-2A/FG-Stress) in the current reports. Some regions overlap; these are not 67 unique functions. A reverb keyword plan against the exact TVB binary selects 11 distinct addresses. The 10 new reverb regions can also be inspected directly with `python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-reverb --find ducking`.

## Verified TVB reverb recurrence evidence

Exact binary SHA-256 `cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9`. `reports/tvb_reverb_feedback.json` includes 191 opcode/operand checkpoints across ten regions and the necessary local numerical constants. Runtime control mapping and measurements are unverified. No vendor calibration arrays or implementation copied into Skelliere.

- Four input diffusion cells (0x5d861e): `y=d-k*x; write=x+k*y`, each with a delay state. These are allpass-shaped cells, not a complete impulse response.
- Eight-lane feedback (0x5d9074): accumulate the eight damped lane values `v_i`; each lane writes `v_i-0.25*sum(v)+(-1)^i*input/4`. This is the familiar Householder matrix `I-2*11^T/8`, an orthogonal linear transform; orthogonality does not establish whole-loop stability with nonlinear and modulated components.
- Per-lane delay and decay (0x5d8a90): delay interpolation between two anchors, sine modulation, two cascaded one-pole damping states, and `10^(-3*d/T)` decay scale, with `T` bounded below by 0.1. Delay anchor units inferred as seconds from the multiplication by the sample-rate field. Effective broadband RT60 is not measured. Optional normalized tanh in the feedback lane.
- Independent phase states (0x5d8ec3): eight phase increments and wraps; exact modulation frequencies and amplitudes not published.
- Ducking (0x5d924c): input-linked peak one-pole with different rise/fall coefficients; `d=max(-60,20*log10(E))` for positive envelope (otherwise -60). `u=clamp((d+35)/20,0,1)`. For positive amount q, wet reduction is `-15*q*u` dB, converted to linear gain with a -100 dB floor branch; nonpositive q gives unity. Actual control mapping/range not established. This is a local algorithm branch, not a complete effect reconstruction.
- Wet tone and output (0x5d93ef): per-channel state `s=a*s_prev+b*x`; `y=x+(tone-1)*(x-s)` followed by a color helper, then wet gain times ducking factor added to dry. Separate native output stores checked.
- Output color helper (0x5d9a70): normalized tanh with drive `h=1+4*c` when `c>0.0001`, identity otherwise. Unlike the prior generic saturation helper, this call is traced from the reverb wet output.

These independent mathematical insights motivate evaluating diffusion, orthogonal FDN feedback, decay-time scaling and input-dependent wet attenuation for Skelliere using independently chosen delay lengths, gains, damping and modulation. Do not claim a matched reverb without licensed reference renders, impulse response analysis and listening. Production Skelliere is unchanged.
