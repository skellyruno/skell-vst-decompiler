# Skell Analyzer v0.2.0 — DSP discovery front end

Continuation of d4387f41081c50fd4f6f0623aa6c3ea83d32437a. Preserve the production-owned ground-truth report and exact source tools: 15 observed Linux Master numeric IDs plus framework bypass, eight verified parameter endpoint joins, 53 Flang source/string candidates. No replacement of existing research. Owner made the repo public; no new proprietary binaries, raw states, audio, or vendor pseudocode committed. Prior Windows build and pass-through smoke passed; artifact upload failed quota. New upload remains conditional on actual gates.

## Added
- dsp_discovery.py: bounded arithmetic/memory/branch heuristic over eligible x64 unwind records, exact module/region hashes, candidates sorted before unresolved. Two real Windows production PE modules each scanned 32 regions; one candidate in each; sparse sampling, not DSP recognition accuracy. Leaf functions and oversized ranges excluded. Explicit RVAs supported.
- dsp_job.py: fixed 32-range worker job, no target execution, private JSON created exclusively without overwrite. Real Flang module produced a report. Four new local unit tests passed across finder and job; three existing owned state tests reran and passed.
- Analyzer v0.2.0: same plugin code SAnl, no new automation or state schema. Explicit trusted Python executable selector, Find DSP module picker, child-process job with fixed arguments and isolated Python mode, timer-based progress/cancel, 180s timeout, private temporary report. No binary or target plugin loaded inside DAW, no analysis in processBlock. Prior report viewer retained. Requires installed Skell Python package (python -m pip install .) and GNU/LLVM objdump on PATH; choose that interpreter, then inner .vst3/.dll/.epl module. New UI code/build and worker launch are **unverified** until Windows CI and real editor inspection. Local JUCE git retrieval failed DNS; no Quick4 screenshot or new VST3 file available yet.
- SkellParamIds: separate JUCE public host inventory for explicit trusted owned Windows bundle plus exact inner module hash. Uses getHostedParameter()->getParameterID() (JUCE VST3 host returns numeric controller ID), validates unique 32-bit IDs, normalized values, module fingerprint before and after. New CI compares actual fixture IDs with predicted IDs and then uploads Analyzer and inventory executable only after successful host gates. No arbitrary vendor execution. Not yet compiled or exercised locally.

## Reproduce
python -m skell_vst_decompiler.dsp_discovery <module> --limit 32
python -m skell_vst_decompiler.dsp_job --binary <absolute module> --output <new absolute .json>
SkellParamIds.exe --authorized-owned <absolute owned bundle> <inner module SHA256>

Next: validate Windows build/UI/worker launch, expand targeted parameter-reader navigation and independent holdout tests, and connect observed numeric IDs to mode-aware sweeps without confusing framework utilities for real DSP. Preserve source-aware ground truth; do not claim complete decompilation from candidate scores. No production changes.
