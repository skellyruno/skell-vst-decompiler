# Automated supported-host capture

Manual FL Studio testing deferred at owner request. Prior 2faa62db0bfef3ddc605a6794644997f272a91fb: 191 regression tests and all eight workflows passed. Preserve the original static research and independent DSP models.

## Local tested backend

The new host_capture module uses the already-used Pedalboard 0.9.23 public API. Native fixture allowlist: Gain, Compressor, Delay; fixed bounded parameter schemas. Each matrix job has a fresh process, explicit timeout, new output directory, source SHA/manifest/header verification, reset flag, requested block size, parameter readback, output WAV hash and metadata compatible with the previous reference_lab/system_id/listening_bridge tools. No silent truncation, padding, resampling, normalization or latency inference. Preserve failures and continue later jobs; a failed matrix exits nonzero. Process isolation is not a security sandbox.

Four focused local regressions passed. Gain control matched its analytical value; wrong hashes, invalid settings, missing case, duplicate jobs and overwrite attempts rejected. Seven fresh-process built-in native compressor renders succeeded at 48 kHz, settings threshold -24, ratio 4, attack 20 ms, release 160 ms. Three separate histories at block sizes 64 and 1024 plus repeat of train at 64: all four comparisons had zero mismatching samples at zero numerical tolerance. Not a claim of bitwise identity of all floating representations. Refit through earlier system-id path: amplitude detector selected on validation, test .078675 dB vs single .376848, dual .442093 and power .134193. Independent fixture output only; no vendor parity.

## Run the native test matrix

Install the existing research dependencies plus the separately installed pinned Pedalboard:

    python -m pip install numpy scipy soundfile pedalboard==0.9.23
    python -m skell_vst_decompiler.system_id generate probes_extended
    python -m skell_vst_decompiler.host_capture matrix probes_extended experiments/host_fixture/fixture_plan.json captures_fixture
    python -m skell_vst_decompiler.system_id analyze probes_extended dynamic_train captures_fixture/train/render.wav captures_fixture/train/metadata.json > train.json
    python -m skell_vst_decompiler.system_id analyze probes_extended dynamic_holdout captures_fixture/validation/render.wav captures_fixture/validation/metadata.json > validation.json
    python -m skell_vst_decompiler.system_id analyze probes_extended dynamic_test captures_fixture/test/render.wav captures_fixture/test/metadata.json > test.json
    python -m skell_vst_decompiler.detector_fit train.json validation.json test.json

All outputs must stay private. Each run uses a new output folder. Cases with creative tails require suitably padded probes. Declared offset zero refers to the returned host timeline, not proof of zero latency.

## Installed VST3 backend (UNVERIFIED)

A separate opt-in path uses the supported Pedalboard load_plugin API only. Windows x64 Python, legitimately installed and licensed plugin, explicit authorization switch, exact absolute VST3 file/bundle path and fingerprint, expected reported version, explicit declared purpose (owned_fixture or reference), host-exposed parameter keys and stage required. Do not load archived arbitrary DLLs, patch or instrument internals, or bypass licensing. The adapter reads all public normalized parameters after setting requested values, records reported latency, and rejects input identity changes or shortened output. It does not verify hidden state, dynamic automation, sample-accurate parameter events, custom routing, licenses or measured alignment. The bundle hash is either a single file SHA256 or digest of sorted relative paths and content hashes. Use only trusted local installations, not cloud CI with private vendor inputs. Parameter enumeration/calibration for actual vendor plugins is not yet performed.

    python -m skell_vst_decompiler.host_capture fingerprint "C:\\Program Files\\Common Files\\VST3\\YourAuthorizedPlugin.vst3"
    python -m skell_vst_decompiler.host_capture matrix probes_extended private_plan.json private_captures --authorized-installed

TVB/VMR: candidate supported-host route only, actual installed formats and compatibility not verified. VMR module selection via public host parameters may not be exposed; a valid module configuration must be established separately. Evo archived DLL is x86 VST2, unsupported here; requires separate compatible 32-bit legitimate host, not a renamed VST3 or generic DLL harness. Do not infer success from fixture tests.

## Real owned Windows VST3 fixture gate

Original tiny stereo JUCE gain effect source and an owned VST3 smoke added. CI builds source against exact JUCE 8.0.12 commit 29396c22c93392d6738e021b83196283d6e4d850, then loads only that CI-built fixture through the same supported adapter. Four tests planned at gains .25/.75 and blocks 64/1024; exact parameter readback and sample error checks. Local Python syntax check passed, no Windows/JUCE build yet: local dependency absent and network DNS failed. No plugin UI; no Quick4 screenshot applicable. Do not report real VST3 hosting as passed until Windows job passes. No vendor execution, proprietary code recovery or production plugin changes.

See reports/host_capture_validation_2026-11-24.json. Previous data-flow/metadata work and all audio probes retained.

## Hardening follow-up
Each installed VST3 specification now requires expected_normalized (one expected 0..1 value per requested parameter); before/after public normalized readback must match and all reported values must remain stable. This is deliberately strict; read-only meters may require supported role-aware handling in a later round. Records process wall time (offline, not real-time CPU) and explicit host-compensated-unverified alignment. Rejects case-colliding/reserved Windows job IDs, validates child source/output identity and writes result summary atomically. Exact Pedalboard 0.9.23 enforced. Five focused local tests passed, 7 fixed-history native renders and 12 additional seeded Gain/Compressor renders at 44.1/48/96 kHz passed. All ten comparisons at 64/1024 or fresh process repeat: 2,370,180 sample values, zero numerical mismatches. Max analytic gain error 1.49e-8. Windows fixture source and CI preserved; real VST3 backend not locally verified. See docs/DSP_LAB_HANDOFF_2026-11-24.md for priorities and blockers.

## Windows build/load failure and targeted correction
Parent 193a6d095f443ec0e5a17a439363c6234ef36114, CI run 45536284379, job 138943557986: pinned JUCE fetched and owned VST3 compiled successfully; all four host captures failed during Pedalboard scan of the outer bundle directory. No DSP renders were produced. Linux job passed 195 tests. Pedalboard issue #433 (https://github.com/spotify/pedalboard/issues/433) reports Windows expects the inner module; Steinberg's official format spec documents Contents/x86_64-win/<bundle name>.vst3. Added deterministic standard Windows module selection, no relocation/patch/fallback, retaining full bundle fingerprint and additional module hash, rechecked after render. Six local host tests pass, including missing/standard/legacy-file path controls. This is a plausible scan compatibility correction, not a confirmed Windows fix until the next owned-fixture CI passes. Preserve the failed run and do not mark reference runtime verified. Manual FL Studio remains deferred.
