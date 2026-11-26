# Conditional-branch and signal-routing evidence — 2026-11-26

Parent c12ada72261716bd1254653b647808dbb0b0b607. Reused cached Quick4 kit and verified all 13 manifest files. Both locally supplied reference files match exact previously documented SHA-256 fingerprints. No vendor execution, vendor source listings or coefficient tables, protection/activation analysis, or production DSP changes.

## Trackspacer

The setup loop has three byte-checked conditional back edges, with independent dual-decoder operand checks on counters and updates supporting two outer passes, eight packed groups and 32 scalar entries. A separate scratch-buffer setup establishes 32 consecutive pointer stores with 31 stride increments and a trailing null slot. These are buffer layout facts, not proof that each row is an independently filtered audio band. Three direct byte-backed calls from the earlier processing candidate reach one local routing helper. Four byte-checked tail targets distinguish scaled copy, ordinary copy, scaled accumulation and unscaled accumulation utilities. Selected vector arithmetic and stores support these roles; two scalar indexed operands differ in decoder formatting (explicit scale-one) and are not counted as strict agreement. A third formatting difference affects a stride LEA. Of 30 selected setup and arithmetic operands, 27 strictly agree after case/space normalization; the other three are retained as discrepancies. Runtime routing, filter centers and Q, gain-reduction law and exact host parameter mapping remain unverified.

## StandardCLIP

Five bounded downstream scopes were audited, including two precision-paired buffer helper paths and a previously unresolved candidate. No clipping transfer or oversampling algorithm has been established. A particularly useful negative control: Trackspacer and StandardCLIP contain copy-like helpers of the same 1,653-byte length, with 1,626 matching byte positions and 346 relative instruction-address/mnemonic matches under each decoder. This strongly supports common utility classification; it does not establish origin or identical full semantics, and should not be counted as recovered vendor DSP. No raw bytes or listings published.

## Verification

Across 11 scopes, 228 direct conditional branches (53 backward), zero rejected conditional candidates, 2324 address/mnemonic agreements and 97 separate direct rel32 edges. Counts are scoped observations, not whole-corpus coverage or proof of loop execution. New original branch_evidence.py validates short and near conditional encodings, signed relative displacement, aliases, fingerprint, scope and executable target. Two new owned regression methods and one prior precision regression pass locally; the initial strict operand comparison rejected three formatting variants, retained rather than force-accepted. Exact source/test Git blobs matched. Full new CI not yet verified. SkellCore unchanged, no UI change requiring a capture. Other targets remain open.
