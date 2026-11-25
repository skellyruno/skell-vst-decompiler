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
