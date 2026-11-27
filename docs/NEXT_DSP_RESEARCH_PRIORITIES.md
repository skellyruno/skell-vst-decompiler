# Active DSP research priorities

Updated 2026-11-27; preserve all earlier reports and approved sounds. This is the research backlog, not a release checklist.

| Priority | Investigation | Current evidence / next gate |
|---|---|---|
| Very high | Pairwise cancellation efficiency | Prepared prefix exact in 45 audio pairs but negligible timing benefit; reduce divisions and hot-loop work with strict cap and reconstruction parity. |
| Very high | Lifted DC blocker | Native direct and factored forms verified, both slower; investigate symmetric/polyphase factorization and explicit state-transition parity. Keep original DC path. |
| High | Lower convolution cost | Paired interpolation reduced median paired time 3.64% vocals, 3.28% music; verify 8x and controlled alias/harmonic response before opt-in transfer. |
| High | Less conservative reconstruction | History-aware cap passed 4,621,824 checks but negligible RMS benefit and 22–27% timing cost; retain as rejected candidate, seek stronger bounded optimization. |
| High | Limiter modulation on longer music | Full available vocals and 90s mixed music completed; gain-step metric and 27 two-tone cases unchanged for history variant. Extend to held-out music, independent stems and level-matched listening; verify longer release behavior. |
| High | Experimental Skell Master integration | Pending; use separate opt-in research engine only after parity/host validation. Do not alter approved default mastering sound. |
| High | Delay tail/headroom and compressor transients | Preserve scheduling and evaluate new candidates on independent material; isolated bass/drum stems still missing. |
| High | Full five-engine Playground | Resume pinned offline JUCE helper build; preserve Classic and Crystal exactly. |
| High | Presence and actual host profiling | Subjective listening pending; verify native VST3, multi-instance DAW CPU/latency and actual UI when changed. |
| High | Read-only vendor evidence backlog | 854 unresolved transfer destinations, 90 boundary conflicts, 692 local candidates; no new vendor replay this batch. |

Reference: [Lifted DC and history-cap research](LIFT_HISTORY_20261127.md). Do not repeat already rejected settings as new experiments. All latest research remains isolated from production.
