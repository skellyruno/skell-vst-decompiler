# Strict indirect-memory operand evidence and vocal-stage stratification

Parent 908a3a2fd7d2a3e0774db94ee2932a16d41a5f1b. Latest library Quick4 offline kit recovered; all 13 SHA-256 checks passed. No GUI or production engine change.

## Native evidence gap
The earlier transfer_triage.indirect_kind function checks FF group opcode, mnemonic, addressing length and presence of brackets for memory operands; it explicitly does not verify the full address expression. This allows a structurally valid instruction to be paired with an incorrect printed memory address. New standalone indirect_address_evidence.py verifies symbolic effective-address terms and signed displacement using ModR/M, SIB and a single optional REX prefix. It compares to a bounded Intel operand grammar, including GNU/LLVM scale order, qword width, and supported RIP/absolute forms. It does not compute a runtime address, dereference anything or infer audio processing. Unsupported prefixes, addressing forms and ambiguous syntax are rejected. Existing classification and corpus reports are preserved; opt-in diagnostic must be replayed on exact owned/source-authorized inputs before revising counts.

## Validation
Four local unittest methods passed. Actual owned Windows PE assembly/link fixture compiled but was not executed. Eight ordinary memory forms, 16 dual-decoder checks. Generated matrix of 16 base registers x 3 indices x 4 scales x 5 displacements = 960 instructions, both GNU and LLVM: 1,920 accepted correct operands, 1,920 rejected modified displacements. Additional tests reject mismatched registers, scale, mnemonic, width, trailing bytes and unsupported forms. Exact tested Git blobs verified. Reproduce from source root: python -m unittest discover -s tests -p 'test_indirect_address_evidence.py' -v (Clang, LLD, GNU and LLVM objdump required for fixture tests). Full hosted CI not yet verified.

## DSP evidence: stage-aware aggregation, no rerender
Re-read the prior private five-track measurement JSON (digest in adjacent aggregate). Separate the 36 excerpts by the recorded processing stage. At the same nominal 4ms compressor setting, the crest-hold versus original peak results are:

| Stage | Count | Lower candidate peak | Median paired peak change dB | Allpass vs linear median paired echo6/echo1 level difference dB |
|---|---:|---:|---:|---:|
| archive-labeled dry | 2 | 2 | -0.520 | 0.093 |
| processed module input | 1 | 1 | -0.004 | 0.178 |
| processed main/full | 18 | 14 | -0.077 | 0.213 |
| processed adlib | 15 | 11 | -0.576 | 0.132 |

The aggregate 28/36 lower peak finding is mostly supported by already processed material (26/34); only two dry excerpts exist here. Main/full material shows smaller median peak change than adlibs. The echo-loss advantage is modest on these vocal segments; flat allpass magnitude under fixed controls is not a guarantee of improved perceptual sound. These are descriptive paired summaries of existing data, not fresh renders, matched-measured-attack comparisons, or independent performances. No change to candidate promotion decisions.

## Remaining
854 unresolved destinations, 90 boundary conflicts, 692 existing local value-flow candidates unchanged. No new vendor binary replay, no vendor DSP reconstruction, no protected engine, preset, licensing, production or UI changes. Private rows and audio stay out of Git. Previous five-track head last observed seven successful workflows and one running; new CI pending.
