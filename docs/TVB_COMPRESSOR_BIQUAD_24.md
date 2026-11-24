# TVB compressor native filter-bank — instruction-grounded reconstruction

**Source:** user-provided `TVB Rack V2.vst3`, Windows PE32+ x64, 126,212,208 bytes, SHA-256 `cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9`.

**Provenance:** the read-only `objdump -d -M intel` view of the original `.text` section at RVA `0x5D07BF`; reconfirmed through the executable's original bytes. No executable code was run or patched.

## New finding: repeated 24-section transposed biquad arithmetic

At RVA `0x5D07B5`, the method checks a processing-mode selector against integer `2` and branches to RVA `0x5D117E` when it differs. The selected branch starting `0x5D07BF` processes a sample at an x64 channel-dependent data pointer. A native `lea rax,[rbx+rbx*2]` plus `shl rax,0x6` computes a **192-byte per-channel state offset**.

The first stage loads filter coefficients from instance offsets `0x520`, `0x524`, `0x528`, `0x52C`, and `0x530`. Native scalar multiply, add, subtract, and state-write instructions implement the following **transposed direct-form II** recurrence:

\[
 y=b_0 x + z_1 \\
 z'_1=b_1x-a_1y+z_2 \\
 z'_2=b_2x-a_2y
\]

Its native instruction sites include **`0x5D07C6`, `0x5D07D5`, `0x5D07DD`, `0x5D07EC`, `0x5D07F4`, `0x5D07FB`, `0x5D0804`, `0x5D0810`, `0x5D0818`, `0x5D0820`, `0x5D0824`**. The first persistent state fields are at `0x718` and `0x71C`. Each subsequent identified group increments coefficient addresses by `0x14` (20 bytes) and states by `0x8` (8 bytes). Exactly **24 stages** pass all the operand-presence checks, ending with coefficient bank `0x6EC–0x6FC` and state fields `0x7D0/0x7D4`. The 192-byte channel stride matches 24 × 8 bytes.

**Interpretation limits:** The evidence establishes repeated per-channel filter-state recurrences and shows the first section's algebra. A filter recurrence does *not* establish whether the signal is wet audio, sidechain detector, or one branch of a complex multiband processor. The compiled branch may combine filter and meter/dynamics calculations; there are more operands after the last state group. We do **not** infer filter cutoffs, Q, gain normalization, 24-to-24 front-end band mapping, phase response, full compression transfer, CPU or sound quality from this evidence alone.

## Why it matters for Skelliere

- The coefficient grouping and persistent state update can guide an independently developed, testable filter-bank abstraction.
- Prefer independently implemented state-variable/TPT designs for prospective dynamic-EQ features rather than copying vendor implementation or replacing current Quad EQ.
- Add offline magnitude/phase, impulse, coefficient-interpolation stability, odd-block, 44.1/48/96 kHz and anti-denormal tests before any host/DAW changes.
- Do not ship a Skelliere behavior change based solely on reverse-engineered equations. Preserve existing APVTS IDs and session compatibility.

## Reproducible checks

```bash
python -m skell_vst_decompiler "TVB Rack V2.vst3" --mode tvb-bank --out local/bank.json
python -m unittest discover -s tests -v
```

Outputs are JSON **summaries only**, with SHA-256, coefficient and state offsets and scope limitations; no original vendor code or binary bytes.
