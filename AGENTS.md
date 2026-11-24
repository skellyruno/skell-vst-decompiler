# Skell VST Decompiler agent instructions

Follow [SkellWorld/AGENTS.md](https://github.com/skellyruno/SkellWorld/blob/main/AGENTS.md).

This private repo is a **read-only binary research and independent DSP design toolkit**:
- Always distinguish machine-code-confirmed recurrences from candidate math and unknown routing/parameters.
- Identify source binaries by SHA-256 and match exact build before using hard-coded RVAs.
- Do not execute arbitrary VST3/EPL/DLL binaries or bypass copy protection, iLok/PACE, activation or licensing.
- Never commit proprietary original binaries, extracted vendor source, fonts, private audio or reconstructed vendor implementations.
- Use independently implemented math only for isolated experiments, then real plugin A/B measurements where authorized.
- Keep original Skelliere parameter IDs, serialized states, plugin IDs, preset names and Tune latency unchanged unless explicitly approved.
- Run local/CI unit tests; status from actual completed runs only. Develop on feature branches and open draft PRs. Do not merge unverified work.

## Mandatory cross-chat continuity
- Treat the active draft PR head as the source of truth, not a chat summary or the main-branch bootstrap. Read docs/RESEARCH_CONTINUITY.md, the existing atlas, and relevant reports before starting. Do not recreate completed work.
- Every substantive batch must persist original Skell tooling changes, tests, and safe machine-readable findings (SHA-256, bounded evidence references, confidence and limitations) in the same feature branch. Update the continuity document and PR description with the exact commit and test status; preserve older reports, correct them with explicit provenance rather than silently replacing them.
- Chat downloads are supplemental, never the only copy of a finding. Keep private source binaries, private audio, vendor pseudocode and proprietary data outside Git and CI. Never upload them to external analysis services.
- Record new upstream tools, inspected source paths, license and integration decision in docs/UPSTREAM_TOOL_REVIEW.md. Use independent implementations and explicit external adapters; no whole-vendor code reconstruction, licensing bypass or arbitrary DLL execution.
