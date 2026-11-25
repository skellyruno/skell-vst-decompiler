# Architecture-first DSP discovery — 2026-11-25

The owner proposed an architecture-first workflow inspired by a Delphi wrapper, a separate C++ engine, and a saved-state corpus. The multiband example's 79 states and 124-byte layout are user-reported research, not independently verified here. Its exact two binaries and extracted state corpus have not been supplied in this batch. Preserve them privately when available; never assume another plugin shares this layout.

## Implemented gates

1. Explicit adjacent PE32+ engine candidates: exact SHA-256, ordinary imports, loader API imports, and ASCII/UTF-16LE filename substring clues. Only a matching import descriptor is classified STATIC_IMPORT; a string is LITERAL_ONLY, not a resolved load or DSP edge. No arbitrary DLL execution, automatic recursive filesystem traversal, delay-load mapping, or protection analysis. x86 and Delphi VMT specialization remain pending; existing legacy metadata reader remains intact.
2. Extracted-state corpus audit: count matching-size blobs, content duplicates, rejected sizes/files, varying offsets, and nonoverlapping analyst-declared mapped/opaque/unclassified spans. A fully covered byte layout is not automatically semantically decoded. Never pass whole FLP/FST containers as extracted states without a verified container reader.
3. Private Ghidra project retention: optional --retain-project on the existing bridge removes -deleteProject, keeps unique job isolation, records requested retention, and preserves default cleanup and no-overwrite semantics. This is manual continuation support, not automatic reuse of existing Ghidra projects. Private projects, pseudocode, preset and project files are excluded from Git.

## Local verification

Prior exact head 163ce35 passed all eight CI workflows. Four new unit tests, seven existing Ghidra bridge tests and 76/76 archived local tests passed. Local archive is older than current full branch. Compiled original freestanding C wrapper and engine using clang x64 Windows target and lld-link. Initial linker failure missing CRT _fltused resolved by explicitly supplying the fixture's integer _fltused symbol in both independent translation units. No target executed. Wrapper imported engine.dll and CreateEngine; GNU objdump independently confirmed the same edge. Scanner also ran on exact supplied Gem Dopamine (15 ordinary imported modules), TVB Rack V2 (36), and VMR rack (32); all expose four common loader API imports, not proof of a dynamically loaded DSP engine. Explicit TVB-to-VMR sibling negative control reported NO_EDGE_OBSERVED. No new native equations this batch. State validation used a synthetic 124-byte fixture (three matching, two unique, one bad length, four mapped bytes and 120 opaque bytes), not the user's 79-state corpus. No installed Ghidra launcher; retained-project behavior tested at command level, existing fake analyzer tests passed; real retention pending. JUCE retrieval failed DNS and is unnecessary for static work. Exact current branch CI pending.

## Reproduce

python -m skell_vst_decompiler.architecture_intake architecture /private/wrapper.dll /private/engine.dll

python -m skell_vst_decompiler.architecture_intake states 124 /private/state1.bin /private/state2.bin --fields /private/schema.json

Fields file: JSON array with offset, length, kind (mapped or opaque). Counts reflect declarations, not automatically inferred semantics.

python -m skell_vst_decompiler.ghidra_bridge /private/engine.dll --rva 0x1000 --ghidra-home /path/to/ghidra --retain-project

The RVA is an illustrative placeholder; choose verified executable targets for each exact binary. Use an ignored local private work root.

## Automation roadmap

Fingerprint and inventory -> dependency evidence -> classgraph and explicit dispatch candidates -> bounded cross-engine observations with existing cache -> utility classification and evidence-ranked DSP candidate queue -> selected private Ghidra plans -> verified state extraction and controlled parameter perturbations -> mathematical hypotheses -> independently implemented probes and authorized host measurements -> atlas with separate confidence and completeness. Reuse existing engine_batch, research_index, classgraph and verification instead of replacing them. Next implement evidence-ranked target planning and deduplication, then safe exact-source checkpoint resumption; add Delphi VMT and FLP/FST adapters on owned fixtures and the available authorized corpus. Keep dynamic loads, labels, inferred equations, measured outputs, and unknowns distinct. Do not promise automatic complete proprietary source reconstruction. Only the decompiler repo changes.
