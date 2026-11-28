# FG-2A: coefficient provenance and scoped coverage (2026-11-24)

## New exact-build evidence

The supplied FG-2A binary matched SHA-256 `6b365ee15dbb94efb9d97b76923445f4ad4f3740194e21363cd9ffbe8df8d573`. The native setup at RVA 0x142340 passes subobject +0x1360 to initializer 0x1423a0. Processing caller 0x156f04 passes that same relative subobject offset to 0x14d590, whose first context pointer becomes RBX. This establishes the relative object relationship for these candidate paths, not runtime object identity or dispatch selection.

The nine initialized weight fields at 0x550 through 0x590 (stride eight bytes) have a common signed dB conversion: sign * exp(log(10)*0.05*d), equivalently sign * 10^(d/20). Both imported math symbols are checked. All nine file-backed dB sources are finite and their concatenated bytes are fingerprinted; their values are not redistributed. All nine matching read endpoints in the linked processing subobject are verified. Runtime mutations are not excluded.

The previous even-order arithmetic now connects to a filtered contribution and a second-order term. An additional branch forms third, fifth and seventh powers, then scales/combines the third and seventh; final independent use of the fifth power is not established. The fourth-power scratch stream also has an additional weighted path. These are local signal operations, not proof of a complete optical gain law.

At 0x142110, the inspected scalar helper paths establish a biased rational transformation, with finite inputs, nonzero denominator, and nonnegative clipping bound: cubic-plus-linear numerator, quadratic-plus-constant denominator, symmetric clipping and an output offset. Its two caller records at offsets 0x238 and 0x270 are checked. Their parameter initialization and active SIMD dispatch are open. Another stereo DF2T filter pair, a later subtraction/addition merge, and a local clipped branch summed with saved input followed by 0x14f340 are verified. The latter routine and ultimate audio gain path remain unresolved. No claims of circuit interpretation, measured harmonic parity, vendor source recovery or licensing changes.

## Coverage toward the user's 80% goal

Use explicit, bounded denominators rather than instruction totals. This pass closes **9/9** weight initialization origins and **9/9** matching coefficient read endpoints in the identified FG-2A polynomial subobject. Six rational-helper field reads have been identified; their six setup origins are not established. Full-module completeness cannot be estimated from static regions or unwind metadata. The high-priority remaining work is the rational parameter setup, filter coefficient writers, host control transforms, actual effect-specific gain application, and authorized local renders. FG-116 and FG-Stress were not newly traced in this pass. The 80% goal is a target, not a verified global percentage.

## Reproduction

`python -m skell_vst_decompiler.vmr_coefficients /private/FG-2A.epl`

Exact fingerprint enforced. 173 opcode/operand checkpoints over 16 added regions; ten math import checks, four explicit scalar dispatch slots and sign mask verified. Repeat report produced byte-identical output. The first rational scalar-add check had a one-byte-short disassembly end boundary; corrected to include the entire store and reran. No raw source binary, raw coefficient array or runnable vendor processor is distributed. Local unit and native regression results are recorded separately. No vendor plugin execution, production Skelliere DSP or UI changes.
