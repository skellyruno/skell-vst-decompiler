# Gem Dopamine and selected VMR native paths — 2026-11-25

Scope: original exact-build static observation only, no executable target launched, no private binary/table/audio committed. Read the owner-supplied full research request and resumed the active draft, not a replacement project. Reconstructed private VMR ZIP from four local parts, SHA-256 353f23373ac05d7b2121c313073f08c708e879d839115d4ce5d30657732f481e; re-extracted module files privately.

## Gem Dopamine
Validated MSVC x64 RTTI: Dolby361 (table 0x755b00) and GemDopamine (0x756800), both with TEffect base. Slot 12 candidates 0x58b510 and 0x58a300 respectively. These are bounded static candidates, not proven host runtime dispatch. At 0x58a300 two embedded object choices (+0x30/+0x4f0) call slot +0x60 and apply output scaling; alternate branch invokes one object and copies input channel records into output. The channel record stride is 0x98. Exact control names and routing are unresolved.

At 0x58b510 three control states approach targets using common smoothing and near-zero cleanup. At 0x58b636 and 0x58b6cd, the same candidate 0x58bbe0 receives different state-object addresses (+0x38/+0x258) for the two channel paths; the second is conditional on channel count. The 0x58bbe0 region calls 0x560150 three times, 0x58c100 four times and then buffer additions. 0x560150 first samples show a second-order recursive filter with three feedforward and two feedback terms, history from object fields and earlier output samples. No coefficients or band frequencies recovered. At 0x58c100, a signal multiplier depends on prior state with a lower bound. The post-multiplier magnitude is compared to that state; rising correction includes a squared difference and a state-specific coefficient, falling correction uses a floor and separate coefficient. A repeated local loop writes updated state and audio. This is a nonlinear envelope-dependent path, not confirmation of the de-esser, exact excitation architecture, or a complete model. Frequency assignments, coefficient initialization, parameter setters, latency, and runtime mode still open.

Utility classification: 0x5612f0 scales 32 float values, 0x561640 adds scaled source to destination over 32 floats, 0x561e60 copies 128 bytes. Do not count these as separate audio algorithms.

## VMR
FG-401: both previously mapped candidate bodies (0x15ede0 and 0x15f490) contain direct calls to 0x15e050. The bounded four-element unroll uses a persistent double state, compares state minus incoming value against zero, chooses one of two supplied retention values, then updates output and state. This establishes asymmetric smoothing, not a proven full compressor gain law or time constant.

AirEQ Air: earlier candidate 0x248db0 calls 0x246e80; the contiguous continuation from 0x246eae reads a new sample, writes circular history, accumulates products against successive coefficients with wrapped history reads, stores output, increments and masks cursor by 0x3f. A 64-sample FIR history is confirmed. Tap weights, filter response, symmetry and phase/latency not established. AirEQ Earth still has navigation only in this batch.

VCC Channel: 0x19ade0–0x19ae27 reads channel-indexed buffers/state and calls 0x176970 twice, incrementing the index to 2. No saturation law inferred. VCC MixBuss candidates inspected for navigation, no additional verified equation this batch.

## Verification
New general scoped_evidence verifier checks source SHA, bounded executable byte-range hashes and selected mnemonic checkpoints. Actual private sources: 11 regions, 113/113 selected mnemonic checks agreed between GNU and LLVM; verifier passed on all four sources (Gem 80, FG-401 13, AirEQ Air 12, VCC Channel 8). Four new focused tests included in 72/72 archived Multi Engine Lab local tests passed; archive not the latest branch. Local tested blob IDs: verifier eca296023081d21693c2417f328f0f2f541c8141, tests 02883e9fd9c464038063364fe7d6b364fbad1213, report 414c4920f9ca9e7d432c71707d754a077bf3e0ad. Manifest deliberately outside root atlas glob. Full current-head CI pending. No actual vendor renders, full DSP reconstruction, CPU, latency or subjective comparison. Local JUCE unavailable, git DNS failed; not needed for static research. No production changes.

Reproduce: python -m skell_vst_decompiler.scoped_evidence "/private/Gem Dopamine-64.vst3" --report reports/native_scoped/gem_vmr_paths.json (repeat for the named EPL files).

Next: trace Gem coefficient setup and true parameter endpoints, FG-401 gain computer, AirEQ Air coefficient generation and Earth path, VCC coloration core; continue the remaining TVB and all 31 VMR research backlog. No claim all 31 are analyzed.
