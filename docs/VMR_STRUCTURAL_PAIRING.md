# VMR — relocation-tolerant function navigation (2026-11-25)

## Why exact-code hashes are not sufficient

Cross-module SHA-256 comparison confirmed large shared compiled-code regions among all 31 VMR engines. However, executable regions can perform structurally similar work while differing bytewise because of relocation, address offsets, compiler decisions, constants, or called destinations. Identical bytes also do not prove identical audible processing when coefficients or state reside outside the code range.

## Three exact-source VCC comparison pairs

From the recovered, fingerprint-verified `VCC Channel.epl` (SHA-256 `73747020e8996938b8e6fdff51004cff4ea85c95f992cbc8bc0d0896a80aad87`) and `VCC MixBuss.epl` (SHA-256 `fe077912d5396577fc6b32bcf0c4ba4b61d5e1f8089e961ce68dae22e1b0b500`):

| Channel RVA | MixBuss RVA | Channel/MixBuss instructions | Ordered normalized mnemonic similarity | Byte-identical? |
|---|---|---:|---:|---|
| `0x176970` | `0x152670` | 134 / 134 | 1.000000 | No |
| `0x176610` | `0x152310` | 49 / 49 | 1.000000 | No |
| `0x19ac10` | `0x172a50` | 131 / 132 | 0.942966 | No |

Both GNU and LLVM individually agree on all normalized instruction locations/opcodes within the selected functions. GNU emits `data16` pseudo-instructions for certain prefixed no-ops; the new matcher normalizes only observed prefixed-NOP forms, not general instructions. The third ratio differs from an earlier raw GNU-only estimate because normalization and explicit address-aligned decoder consensus were added. The first two functions show **structural instruction equivalence**, not vendor model/sound equivalence. The third indicates close code-path similarity but requires detailed field/parameter provenance.

## New independent research tool

`skell_vst_decompiler/structural_match.py`: compares two *explicitly selected* bounded, unwound, executable regions, using dual-decoder consensus, SHA-256 scope hashes, ordered normalized mnemonic similarity and source fingerprints. It never loads/executes the binaries, and never writes vendor disassembly to a report. Use it to propose likely variant-to-variant function relationships after shared-code prioritization. It does not automatically label DSP versus utility.

Owned Clang/LLD Windows PE regression built two variants of an original source-known processing wrapper; native instruction similarity passed with a threshold >=0.90 despite different function-byte hashes. Initial test fixture was shorter than the minimum bounded scope; added more controlled operations. A further GNU prefixed NOP formatting discrepancy was fixed before final VCC dual-decoder verification. Two new unit tests and the owned PE smoke passed. No sample-rate, sound, host, screenshot or production-plugin testing is claimed.

Commands:

```sh
python -m skell_vst_decompiler.structural_match '/private/VMR/VCC Channel.epl' 0x176970 '/private/VMR/VCC MixBuss.epl' 0x152670
PYTHONPATH=. python tests/structural_match_smoke.py
```

Next: use verified VCC pairing to trace mode controls, independent coefficient fields and processing outputs. Add source-known negative controls and test classification precision before deploying any automatic DSP-versus-utility labels. Preserve all previous VMR research.
