# TVB limiter release and delay timing research — 2026-11-25

Read-only, exact source SHA-256 cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9. Seven bounded regions, 170 mnemonic checkpoints (some overlap prior reports), 13 math calls and 20 scalar constants. No vendor execution, raw coefficient arrays, reconstructed vendor implementation, or private audio committed.

## Limiter
- 0x5dd171–0x5dd1bd: signed mode field is clamped to 0..2 and indexes a paired scalar record; first component used in the previously established knee path and second in release setup. No host labels or raw table published.
- 0x5dd20c–0x5dd2d5: four exponential retention calculations. Single-envelope recovery depends on adjustable release field, selected multiplier and sample rate. Dual-envelope release uses the same selected multiplier with fixed 60 and 400 ms bases; secondary attack uses a fixed 20 ms base (not the 0.02 ms primary attack from the earlier setup). These are coefficient time constants, not measured audible settling times.
- 0x5ddcc3–0x5ddde1: the alternate dual mode independently chooses rise/fall retention for two reduction states then selects their maximum. Single mode uses previous linear gain converted to dB. The branch flag and numerical mode field are distinct; don't conflate them or infer control names.

## Delay
- 0x5d67be–0x5d68ad: direct time field or tempo-based target, using 60000/BPM times division multiplier with 20 ms lower bound and configured upper bound for valid positive tempo/configured range. Conversion to samples; initial state adopts target, later changes use a 120 ms exponential time constant.
- 0x5d68eb–0x5d69e4: two cutoff-dependent exponential retentions and separate input detector coefficients corresponding to 5 ms attack and 250 ms release. Full cutoff range/knob mapping not established.
- 0x5d69f0–0x5d6bac: minimum one-sample read, fractional linear interpolation; cascaded first-order filter states and difference-based feedback. Independent stereo write mode versus cross-channel write mode where averaged dry enters one delay line. Feedback amount and time selection are independent controls.
- 0x5d6bac–0x5d6d44: linked absolute-peak detector; level conversion with floor, depth-scaled ducking above -35 dB and saturating at -15 dB detector level. Full normalized depth corresponds to -15 dB wet attenuation. Gain and separate ramped wet level multiply interpolated taps before addition to dry. Ducking does not modify the prior feedback write in this local loop. Host parameter scaling and runtime mode behavior not yet confirmed.

## Verification
Manual operand inspection plus cross-decoder GNU/LLVM mnemonic agreement at all 170 checkpoints; region byte hashes anchor exact source. Existing exact-build verifier ran twice on private binary with identical counts (170/20/13/7). Three focused local regressions passed; archived Multi Engine Lab baseline plus these tests 71/71 passed, not current full-head suite. Existing verifier local blob b114153864027d88e116cd1dc7b985c4e42ecdb9. Report blob c24f7b805abc0dfaf23b0480ce07053fb063f0ab; test blob 33edb07c98dc7193a52c5b5dae0d0da221b2d865. Previous exact head 00d44bd87a3ae72f981f1180fa149a7d14c7b3d8 passed all eight CI workflows; new CI pending. No full vendor reference audio or plugin latency claim. Local JUCE dependency absent and git DNS failed; not required for static-only research. No other repository modified.

Reproduce: python -m skell_vst_decompiler.tvb_limiter_setup "/private/path/TVB Rack V2.vst3" --report reports/limiter_setup/tvb_release_delay.json

Next: trace named parameter setter provenance for delay and limiter, map wet/feedback routing variants, and validate actual latency and peak error separately. Research only.
