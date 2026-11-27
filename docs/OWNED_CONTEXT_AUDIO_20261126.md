# Owned context and controlled audio calibration — 2026-11-26

Parent e66a71e2669dfa07123d3b9fa3e8f3c03f853571. Reused cached Quick4 kit (13/13 manifest checks passed) and existing verified independent engine headers, not a new UI or native plugin build. All 19 existing local unittest methods passed. New owned-only benchmark completed successfully. Exact three new source blobs match locally executed files; independent engine headers match parent Git blobs.

## Context is essential

New role_context.c contains source-known audio gain, hard clipping, geometry scaling, buffer clearing and a shared indirect callback dispatcher with four named wrappers. Compiled for Windows x64 at O1/O3 with Clang/LLD, no entrypoint and no identical code folding. Static fixture windows selected from the owned linker map (nine symbols per build, may include padding). The audio gain and UI geometry windows are byte-identical within each build: 48 bytes at O1 and 128 at O3. Both have equal arithmetic counts (1/3) and guarded store counts (1/2). The hard clip fixture gives zero detected transformed stores at both levels although its native outputs are correct. Therefore opcode, arithmetic-density, shape and local-value-flow evidence cannot identify audio semantics alone, and absence of a local-store pattern is not proof of no DSP.

The same dispatcher contains one verified indirect register site per build. A separate native build of the same owned source was actually executed with explicitly supplied callback pointers and named wrappers. All eight callback and eight wrapper cases matched their independent sample oracle exactly. This does not establish Windows runtime paths or any third-party indirect destination. Cross-window reconciliation found one guard per owned build. Earlier 692 candidates, 854 unresolved destinations and 90 boundary conflicts remain unchanged. No production classifier label promoted on these fixtures.

## Controlled audio

New owned_audio_probe.cpp adapter calls existing independent PresenceEngine, ProgramLeveler, ColorEngine, ColorOversampled2x and ColorOversampled. Built native shared library with GCC -O2 -Wall -Wextra -Werror. Generated tones at 44100, 48000 and 96000 Hz. At all 15 engine/rate combinations, tested output finite, block partitions 1 versus 257 samples identical, dry response exact after expected delay, and impulse dry delay verified (0 samples for three base engines, 40 for two oversampled engines). This partition check is harness-level, not plugin host validation.

Presence at low input amplitude: 100 Hz approximately 0 dB and 9 kHz +2.984 to +2.990 dB. Leveler at 1 kHz and .5 peak, -18 dB threshold, ratio 4, attack 4 ms, release 120 ms: steady gain about -8.69 dB at all rates; stereo linked ratio error <=2.78e-17. Recovery tested with 40 ms versus 1 s high-level bursts, then a quiet tone. At 48 kHz the first 10 ms of recovery is -8.34 versus -8.69 dB and after 100 ms -6.71 versus -7.62 dB, respectively. Near unity after 1 s. This shows duration-dependent recovery in our independent leveler, not FG-2A matching.

Color: 11 kHz, .5 peak, +12 dB drive, .12 asymmetry, fully wet, last one second of a two-second render. Selected folded-third-harmonic amplitude relative to output fundamental:

| Rate | Frequency | 1x dBc | 2x dBc | 4x dBc |
|---|---:|---:|---:|---:|
| 44.1 kHz | 11.1 kHz | -15.48 | -107.93 | -105.73 |
| 48 kHz | 15 kHz | -15.48 | -114.38 | -111.35 |
| 96 kHz | 33 kHz (not folded) | -15.48 | -15.48 | -15.48 |

2x and 4x reduce the selected folded component substantially at lower sample rates. 2x is slightly lower on this particular test, not evidence of superior overall alias rejection or CPU. Both have 40-sample dry delay. No production engine selection or changes made.

## Reproduction

Run `python benchmarks/owned_context_audio.py --output owned_context_audio.json` from the repo root, without Python optimization. Requires native Linux compiler, clang/lld-link, both GNU and LLVM objdump. Benchmark compiles only the included owned sources; does not execute Windows or vendor binaries. Full local JSON SHA-256 92302a4cfc51d4f1dcf1ab9b05715cab80f7e9782d8ea442ff0a640544c1bb1a. Machine-readable summary saved in reports/ground_truth/owned_context_audio_2026_11_26.json. Parent CI status recorded in summary; new CI not verified. No vendor audio, actual music, production VST3, host latency/CPU, protected-code analysis or sound equivalence claimed.
