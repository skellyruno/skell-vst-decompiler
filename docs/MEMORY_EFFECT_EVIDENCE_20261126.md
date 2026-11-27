# Memory-effect evidence — 2026-11-26

Parent 1ef74cfad0a5a23cd66da1e971b8108fd006ce94. Reverified eight exact source fingerprints and all 432 previously surveyed scope hashes, plus identical selected FP counts per scope. Reused cached offline kit: 13/13 manifest files passed. Current dependency blobs matched prior commit. This is static research only; no vendor execution, licensing/protection analysis, raw vendor values, source, listings or reconstructed algorithm published.

## New evidence gate

Original memory_effects.py validates a narrow set of legacy SSE memory operand encodings (prefix, opcode, ModRM, SIB, register extension, signed displacement, complete span) against GNU and LLVM operand text. Counts explicit reads/writes by effective-address syntax; RBP separately marked frame-or-general rather than presumed stack, RIP-relative not presumed read-only, other general-register bases not presumed audio buffers. No target values read. A separate deliberately narrow contiguous read/one arithmetic instruction/write pattern requires matching memory expression, precision and destination register plus byte-verified arithmetic register operands. Does not prove reachability or audio identity; zero matches is not proof of no processing.

## Results

| Module | Memory sites | Prior high candidates | General-register read/write candidates | Local patterns |
|---|---:|---:|---:|---:|
| StandardCLIP.vst3 | 2376 | 25 | 23 | 0 |
| Trackspacer25.vst3 | 2258 | 20 | 13 | 0 |
| FG-2A.epl | 2615 | 20 | 18 | 0 |
| Auburn Sounds Panagement 2-64.vst3 | 3669 | 43 | 24 | 11 |
| DeeDoubler.vst3 | 1937 | 24 | 12 | 0 |
| MixWave DW Fearn VT-5.vst3 | 3868 | 34 | 24 | 0 |
| SSL Fusion Stereo Image.vst3 | 2238 | 33 | 20 | 3 |
| MB MixHead.vst3 | 2384 | 47 | 31 | 1 |

21,345 selected memory access sites: 7,744 general-register reads and 4,070 writes; 3,055 RIP-relative reads and 10 writes; 2,346 explicit stack-pointer reads and 2,272 writes; 866 frame-or-general reads and 982 writes. Zero operand mismatches for supported jointly bounded byte forms; unsupported encodings, missing decoder boundaries, terminal instructions and implicit memory accesses are outside this denominator. 165/246 previously unflagged high-arithmetic windows contain both selected general-register read and write forms. 15 narrow local patterns in five windows (Panagement 11/three, SSL 3/one, MixHead 1/one); none was flagged by the previous shared-shape comparison. The comparison has incomplete coverage; no semantic provenance or actual audio path proven.

## Validation

Two new locally executed unit methods pass: independent byte-form/operand tests and compiled owned Windows PE with both actual decoders. Fixture requires two positive scalar/packed patterns and excludes four near-miss patterns (stack pointer, different address, wrong destination register, precision mismatch). Fingerprint/range rejection, malformed instructions and terminal exclusion also checked. Reran two prior anchor-survey tests: four local test methods passed in total. Exact new source/test hashes match Git objects. Parent CI last observed seven passed, one running. Latest full CI unverified. The report preserves aggregate evidence and five bounded candidate windows; local full 432-row JSON identified by SHA-256. No production DSP, plugin UI, preset or SkellCore changes.
