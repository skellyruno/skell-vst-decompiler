# FG-2A filter and feedback provenance

## Scope and evidence

Exact FG-2A source SHA-256 `6b365ee15dbb94efb9d97b76923445f4ad4f3740194e21363cd9ffbe8df8d573`. The previous polynomial provenance report remains intact. This follow-up is static evidence about bounded local operations, not a reconstructed vendor processor.

At 0x14b805 the setup path computes parent +0x1360, the same relative offset supplied to the candidate processing function 0x14d590 by caller 0x156f04. The six generator calls and their 48-byte stack-output records are linked to the copy stores at object offsets 0x2f0, 0x360, 0x3d0, 0x440, 0x4b0, 0x520. Exact register-to-stack source loads and destination stores are verified. Each record supplies five active coefficient fields to two distinct state pairs; the sixth slot is not consumed in the inspected recurrence. All 30 active fields and 60 per-channel read sites are identified, not the full internal generator equations. Six record links do not prove runtime dispatch or live object identity.

The caller at 0x14e2a6 supplies the same relative subobject to 0x14f340. Its scalar-tail path at 0x14f6b3 adds the scaled input to saved feedback, selects a sign-dependent identity/quadratic/affine magnitude curve, restores sign, writes the local result and scales the feedback for the next sample. The feedback parameter is at +0x1d8; scale and state are distinct. Following filtering, 0x14facd computes a first difference and retains the previous sample. A later vector difference is written to a supplied output buffer (two stream passes, stride 0xb0). Runtime dispatch and complete host gain/output routing remain unverified.

Setup call 0x14b9fc supplies the +0x1360 subobject to 0x149a90. This identifies 14 curve-field writes (seven per polarity) and three associated scale/feedback writes. The quadratic transition calculations use A=(m-1)/(2*(H-L)), B=1-2*A*L, C=(1-B-A*L)*L for ordered distinct breakpoints. Thus the lower transition matches identity value/slope and the upper transition matches affine slope; the independent affine intercept must not be assumed to guarantee value continuity at H. The exact finite-input local calculation is verified, not every control-to-calibration scalar origin. Neither the rational parameter records +0x238 and +0x270 nor full generator internals are resolved here. Prior reports counted six rational-helper field roles; across two caller records these may correspond to twelve distinct slots. No invented whole-module coverage denominator.

## Reproduction and verification

`python -m skell_vst_decompiler.vmr_filter_provenance /private/FG-2A.epl`

17 evidence regions; 256 instruction checkpoints, six filter record links, 30 active coefficient fields, 60 channel reads, 17 feedback write endpoints. Repeated exact-source report byte-identical. Initial verifier failed on mistyped store RVA, corrected from decoded source. A stale generated atlas initially failed the deterministic atlas test; regenerated and reran. Final 65/65 local tests passed, compileall passed, both existing independent native prototype regressions passed at four sample rates. No new vendor audio renders or production DSP/UI changes. No original vendor binaries or raw calibration arrays are included.
