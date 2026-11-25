# Cross-engine behavioral matrix and selective Spacer — 2026-11-25

Parent 71219f9a9784aa4c0d118582f6f91f28a236da2c all eight workflows passed. Additive research only; previous evidence and original engines retained. Restores the previously unpushed coherent spectral probe and native baseline harness.

Original 17-band maximum half-octave filter bank, two cascaded detector bandpasses and sequential normalized notch blends. Bilinear bandwidth correction and final fixed-index center grid reduce rate dependence; no vendor coefficient or code use. At 48 kHz 1 kHz detector: prior -6.419297 / -9.046539 / -6.578848 dB, candidate -0.100691 / -8.793570 / -0.138154 dB at 100/1000/9000 Hz. Final maximum off-target magnitude 0.142235 dB over the 4-rate, 3-detector, 3-tone matrix. Intended cuts at least 4.5 dB in those tested cases; not proof of continuous-band performance. Right unaffected in LR case, tested zero-depth exact and initial impulse without dry delay, M/S unity/isolation and nonfinite input. Fixed coefficients require prepare/reset, not automation-ready. Native benchmark includes input generation: 1.1444 versus 17.9869 us/48 stereo frames on local Linux, not DAW CPU. Optimize before integrating; no production edit.

The new block gain model uses least squares and residual, not a proof of compression topology. Harmonic diagnostic groups collisions and reports folded candidates only, not total alias energy; one-second sideband metric requires coherent frequency grid. Per-tone complex gain uses aligned detector-off baseline; phase is modulo 360, not latency, and non-tone residual is not THD. -240 dB is a numerical floor. Use licensed/authorized aligned reference renders, do not infer source implementation.

Exact existing header blobs verified for Spacer3, IndependentEngines, ColorOversampled and StackedFlanger. New native tests render existing ProgramLeveler (95% recovery 425/475/495 ms after 40/200/1000 ms drive), Presence (9 kHz +2.989/+1.920 dB at .04/.3 input scale against phase-matched unity filter baseline), Color (1x/2x/4x, 2 tones and 3 amplitudes) and StackedFlanger (carrier 1 kHz, 4 Hz modulation, depths 0/.2/1 ms). For 11 kHz/.5 peak, selected 15 kHz folded candidate -15.479/-114.367/-111.349 dBc; 2x and 4x output sample peaks 1.109/1.117, maximum 1.23075 in all cases. No sound parity or safe true-peak guarantee. Need output headroom/limiter interaction and broad sweep.

Nine focused Python units passed; both optimized and ASan/UBSan native matrix runs passed; optimized/sanitized Spacer gain matrix identical, cross-engine reports identical. Full exact-head CI pending. No vendor binaries, private audio, production plugin, JUCE, UI or Windows artifact changes.

## Reuse existing evidence rather than re-derive

| Evidence | Existing report | Use with new measurements |
| --- | --- | --- |
| TRACKSPACE / TVB dynamic EQ | reports/native_scoped/trackspace_context_and_consumers_2026_11_25.json | Cross-frequency sidechain matrix; stereo modes and attack/release |
| FG-116, FG-2A, FG-401, FG-Stress, TVB | reports/vmr_control_streams.json; reports/vmr_fg2a_filter_provenance.json; reports/tvb_dynamics_equations.json | Short/long drive gain trajectories, level sweeps, linked stereo; compare known local structures only |
| VCC, Gem, AirEQ | reports/native_scoped/gem_vcc_deeper_signal_graph.json; docs/DEEPER_DSP_ENGINES_2026_11_25.md | Harmonic/alias fingerprints, level-dependent spectral response, separate phase and delay |
| Master and Flang | reports/ground_truth/production_owned_2026_11_25.json | Owned exact parameter changes; compare scalar gains, output peak and sidebands |
| A1TriggerGate | reports/native_scoped/a1_anchored_discovery.json | Aligned step and pattern timing, residual and recovery |
| TVB reverb | reports/tvb_reverb_feedback.json | Existing impulse/tail energy and wet duck tests; next reuse across rates |
| VMR 31 module corpus | reports/rack_intake/vmr_shared_code_2026_11_25.json | Use prior SHA-bound scope shortlist; do not count utility/shared scope as algorithm recovery |

No new vendor binary analysis in this batch. Existing structural evidence is a hypothesis guide, not reference render data.

## Reproduce (little-endian Linux)

```sh
python -m unittest discover -s tests -p 'test_spectral_probe.py' -v
python -m unittest discover -s tests -p 'test_behavioral_metrics.py' -v
g++ -std=c++17 -O3 -Wall -Wextra -Werror experiments/engine_lab/compare_spacer_selectivity.cpp -o /tmp/skell_spacer_compare
/tmp/skell_spacer_compare
PYTHONPATH=. python tests/spacer_selectivity_smoke.py /tmp/skell_spacer_compare
g++ -std=c++17 -O3 -Wall -Wextra -Werror experiments/engine_lab/native_behavior_matrix.cpp -o /tmp/skell_behavior_matrix
PYTHONPATH=. python tests/native_behavior_matrix_smoke.py /tmp/skell_behavior_matrix
```

See reports/cross_engine_behavior_2026_11_25.json. Preserve draft and no production changes until real reference A/B, CPU, and host validation.
