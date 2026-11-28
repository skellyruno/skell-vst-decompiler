# Evidence-round protocol

Adopt the user's supplied LuxeVerb/Convolver report structure, without treating its reported findings as independently verified or applying its plugin-specific internals to another binary. Preserve the current read-only repository and independent implementation rules.

| Marker | Evidence required |
|---|---|
| [DECOMP] | Direct instruction/decompiler observation with exact source hash, bounded range, tool and version; static facts only. |
| [DATA] | Direct file, preset, parameter or metadata observation with exact source identity and provenance. |
| [EXEC: reference] | Measured output from the legitimate installed reference in a supported host; record version, settings, rate, block size, reset, latency and input/output hashes. |
| [EXEC: fixture] | Actual run on owned code or independent test implementation; never target parity. |
| [MODEL] | Independently authored candidate with hypotheses, fit inputs, separate validation/test inputs and errors. |
| Not confirmed | Missing evidence, disputed paths or an unperformed test. |

For each round record date, commit, target binary fingerprints, exact tools and versions, inputs, observations, validation, failures and remaining unknowns. Record external documents as public sources, not DECOMP. Preserve older evidence and correct explicitly. The same result may combine tags only if each has its own support. No auto promotion from agreement or small numerical error.

## Workflow
1. Read-only inspection and bounded decompiler summaries, keeping proprietary raw data and pseudocode private.
2. Public host/API parameter inventory and repeatable reference capture. Prefer automated ordinary supported host rendering of legitimately installed plugins where authorization and runtime permit. TVB and VMR need their working licensed installation; Evo is x86 and needs a compatible 32-bit host. Do not execute arbitrary DLLs, modify vendor vtables, inspect private object memory, bypass protections, or recreate vendor object layouts under current AGENTS. A separate engine export in the supplied report is not evidence that other plugins expose the same interface.
3. Calibrate on owned DSP fixtures; compare independent model outputs to authorized reference outputs, with matched source, stage, rate, settings and explicit transport alignment. Keep target and model identity separate.
4. Report first out-of-tolerance sample, channel, block and aggregate residual as diagnostics. Compare distinct test histories and independent performances; do not tune on final test. Numerical agreement is not implementation identity.
5. Run native tests, sanitizers, and real audio/host tests before production changes.

New opt-in flag on the existing aligned WAV bridge:
    python -m skell_vst_decompiler.listening_bridge PROBES CASE REFERENCE.wav CANDIDATE.wav REF.json CAND.json --first-difference

Tolerance abs(error) > 1e-6 + 1e-5 * abs(reference) by default, 256-frame diagnostic blocks, zero-based indices. No inferred alignment or gain correction, no internal state tracing. Report first violation and all-sample absolute/RMS residual. No violation means within the stated tolerance for this pair only. Existing output shape unchanged unless requested. Tested locally with five owned controls including actual WAV bridge and wrong-stage rejection. Reference-host automation remains unimplemented. No target execution or new vendor source recovery.

Prior dcd98f81b8e95086018489048deb9a7979869f6a: 186 regression tests and all eight workflows passed, including actual independent native compressor smoke. Source hashes and test results archived.
