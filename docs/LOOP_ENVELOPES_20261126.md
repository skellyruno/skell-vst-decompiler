# Backward branch envelopes and traversal evidence — 2026-11-26

Parent 7f3d89a088b181bc7f9bd1590b0ae1b5bf5c02e0. Reused newest cached Quick4 archive, all 13 manifest checks pass. Local prior PE snapshot mismatch corrected; exact current pe.py, disasm.py and local_call_contracts.py Git hashes verified. Eight source fingerprints and 47 prior scope hashes rechecked, identical replay after dependency correction. Two new owned-fixture test methods plus one prior method passed. Full new CI pending.

## Conservative loop evidence

New original loop_envelopes.py requires byte-backed short/near conditional backwards branches, both decoded destinations, both endpoint addresses and matching address sequences inside bounded scopes. Does not infer dominance, runtime execution or complete CFGs. 208 verified intervals, 59 contain at least one of a narrow set of matching floating-point arithmetic mnemonics. This is candidate prioritization: intervals overlap, arithmetic counts are not unique DSP instructions.

| Target | Scopes | Intervals | With selected FP arithmetic |
|---|---:|---:|---:|
| StandardCLIP.vst3 | 5 | 35 | 13 |
| Trackspacer25.vst3 | 6 | 28 | 17 |
| FG-2A.epl | 8 | 26 | 24 |
| Auburn Sounds Panagement 2-64.vst3 | 5 | 0 | 0 |
| DeeDoubler.vst3 | 7 | 9 | 5 |
| MixWave DW Fearn VT-5.vst3 | 6 | 50 | 0 |
| SSL Fusion Stereo Image.vst3 | 4 | 60 | 0 |
| MB MixHead.vst3 | 6 | 0 | 0 |

Trackspacer main processing candidate has nested-looking intervals with 137 and 135 matching arithmetic sites respectively; FG-2A coefficient generator and earlier processing candidate contain intervals with 284 and 150; DeeDoubler has a 50-site candidate. These are priorities, not independent confirmed DSP stages. VT-5 and SSL have many structural intervals but no selected arithmetic inside them, so don't treat those envelopes as recovered EQ/stereo processing. Panagement and MixHead yield no eligible backwards intervals in this selection; absence is not evidence they lack DSP. Additional data-dependent routing remains unresolved.

## StandardCLIP traversal

45 selected operand checks agree (32 strict, 13 after scale ordering/symbol-label normalization). Both scalar call candidates load the same relative object pointer and use the same virtual slot. Path A uses consecutive sample positions within each buffer; Path B advances across a list of buffer pointers and updates the sample position, with a separate outer callback and counter changes. Both inner and outer backward branch intervals byte-checked. The prior inference of actual clipping behavior is still not established: no verified destination function, nonlinear law, sample-rate ratio or resampler filter.

## Limits

Static-only research. No third-party execution, protection bypass, vendor listings, coefficient values, private audio or reconstructed vendor implementations uploaded. Production plugins and SkellCore unchanged; UI not modified. Full local corpus report hash recorded in machine-readable summary. Prior CI seven successful, one running when checked; new exact head CI required.
