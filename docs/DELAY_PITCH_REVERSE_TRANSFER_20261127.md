# Cross-plugin research transfer: delay, pitch and Reverse

Parent 662706b5d60239a7b4cdce7da644333bd8494ba2; all eight CI workflows passed. Cached Quick4 kit 13/13 verified. Prior SkellCore presence portability follow-up b03e11d: all four workflows passed. No new vendor static replay; backlog stays 854 unknown destinations, 90 boundary conflicts, 692 local candidates.

## Skellay — independent new delay

[4175b662](https://github.com/skellyruno/skellay/commit/4175b662b6545ce66295dd96a32eb909da692abf). Independent two-read-head, shared stereo feedback history; 25 ms time-jump crossfade, 10 ms wet/feedback/cross smoothing, feedback bounded .95, preallocated default 2 seconds. Optimized + ASan/UBSan test passed at 8/44.1/48/96/192/384 kHz; integer and fractional impulse, independent crossfade oracle, dry endpoint, tail and hostile controls. 36 private vocal excerpts, 108 native renders (dry/fixed/time jump), 36 exact dry and 72 nonzero tails; no sample overload. Default ring 768016 bytes at 48k. Windows experimental VST3 workflow passed at this commit, but new kernel is not connected to plugin model/state/UI. Classic/Modern/Bank untouched. No claim of new selectable model, tempo sync or DAW validation. Next gate: additive state/model integration, comparison against the three existing engines, actual editor capture.

## SkellyTune Mini Playground — required candidate arena

[1a32b8f](https://github.com/skellyruno/skelltune-playground/commit/1a32b8f033c859ff9d5a30b6cda3a92bc502c5eb). Exact parent source archive key blob and pinned SnapCore hash verified. Compiled local portable four-engine renderer. Two distinct dry vocals, 16s at 44.1k, four speeds (0/10/25/100 ms), 32 baseline/final pairs / 64 renders. 110 sample common PDC; zero overload. Classic and Crystal 16/16 byte-identical protected pairs. TESTTUNE eight exact; META existing final policy shows mixed metrics (median pitch 5.53685 -> 5.49469 cents, envelope 0.92733 -> 0.94907 dB, coverage 95.13 -> 95.35%). No further promotion. Fixed laboratory scale not verified song key. Reusable private cross-build gate added; full fifth engine (MetaTune 2.5) local validation remains blocked by full JUCE target, no substitute. All future original pitch candidates must compare against existing five engines using actual dry recordings, matched transport, no material envelope/coverage/level/CPU regression, protected references unchanged. Existing engines and UI untouched.

## Skell Flang — protected Chorus/Flang

[fad039c](https://github.com/skellyruno/skell-flang-vst/commit/fad039cdcfc6118288168418b6ea16ab59d6cbb3). No production Source changes. Investigated isolated original Reverse silent octave tap skipping; complete timing run timed out. Three-input subset two dry/one processed; each candidate 9/9 exact. Inner-loop branch median paired savings +28.33/-10.86/+8.33% (zero/active/alternating shimmer); compile-time specialized outer choice +34.06/-4.18/+16.03%. Reject promotion given active-path slowdown and missing exact full local source; commit benchmark only. Need full actual EngineBank, complete corpus and host test before integration. Chorus and Flang unchanged by design.

## Remaining

Other plugin adoption is still planned, not implemented in this batch. Master headroom/alias/true-peak on real music, Preset compatibility/CPU, Spacer instrumental leakage, Rack full integration. No private audio or individual recording metrics in Git, no vendor implementation reconstruction or protected-engine changes. No new Quick4 editor capture (no UI change). New latest CI not all verified.
