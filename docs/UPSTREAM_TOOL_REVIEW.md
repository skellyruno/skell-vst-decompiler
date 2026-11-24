# External tool review — 2026-11-24

These links supplement the established Ghidra/RTTI/Rizin workflow. Reviewed upstream README and selected sources; no upstream tool installed, executed or vendored in this batch. Do not send private binaries or analysis to external LLM providers.

| Project | License | Evidence reviewed | Skell decision |
|---|---|---|---|
| [Revenant](https://github.com/DatanoiseTV/revenant) | Apache-2.0 | [README](https://github.com/DatanoiseTV/revenant/blob/main/README.md), [cache](https://github.com/DatanoiseTV/revenant/blob/main/revenant/pipeline/cache.py), [verification stage](https://github.com/DatanoiseTV/revenant/blob/main/revenant/stages/verify.py) | Adopt the concept of input/dependency fingerprinted stages and independent claim review. Do not use its automated vendor reimplementation or cloud provider workflows. Implement deterministic local checks first; no score averaging or automatic confidence promotion. |
| [Practical Reverse Engineering](https://github.com/DatanoiseTV/practical-reverse-engineering) | Book CC BY-SA 4.0; example code and build assets alternatively MIT per README | [README](https://github.com/DatanoiseTV/practical-reverse-engineering/blob/main/README.md) | Reference for analysis methodology, automation and limitations; no book text copied. Scope to lawful, read-only owned fixtures and permitted audio research. |
| [VST.NET PluginInfo](https://github.com/obiwanjacobi/vst.net-plugininfo) | LGPL-2.1 | [readme.md](https://github.com/obiwanjacobi/vst.net-plugininfo/blob/main/readme.md), [Vst3PluginModule.cs](https://github.com/obiwanjacobi/vst.net-plugininfo/blob/main/Jacobi.VstPluginInfo/Vst3PluginModule.cs) | Its VST3 factory interface retrieves vendor, name, category, subcategories, version and SDK version, but loads the DLL, calls initialization and factory methods. Keep outside the read-only analyzer; consider an isolated, explicitly authorized owned-plugin host test later. Do not claim static metadata equals factory output. |
| [Towel-Decomp](https://github.com/towelwet/towel-decomp) | No declared license in retrieved repository metadata | [README](https://github.com/towelwet/towel-decomp/blob/main/README.md), [DecompileAll.java](https://github.com/towelwet/towel-decomp/blob/main/DecompileAll.java) | Already evaluated earlier. Its whole-program Ghidra exporter is not a replacement for our bounded selected-function exporter. Retain the original Skell implementation, isolated projects and local-only pseudocode. No code copied. |

## Implementation policy

1. Immutable source fingerprints and evidence hashes are the first checkpoint.
2. Cross-check archived structured reports against independent metadata, with negative regression tests; preserve conflicts and unknowns instead of forcing agreement.
3. Track tool/version/config/dependency inputs in future cache keys, and reject stale or mismatched results.
4. Test integrations on owned fixtures; a successful adapter test is not proof that the upstream engine ran.
5. Keep plugin metadata from trusted host measurements distinct from file metadata, and keep measured original DSP behavior distinct from static hypotheses.

Actual integration work remains scoped to the existing Skell tools. The archive preservation test validates consistency of historical records, not the accuracy of the original disassembly or vendor runtime behavior.

## Offline interface extension

Inspected [Revenant report model](https://github.com/DatanoiseTV/revenant/blob/main/revenant/models/report.py) and [report stage](https://github.com/DatanoiseTV/revenant/blob/main/revenant/stages/report.py). Added a metadata-only adapter consuming its top-level report.json: exact SHA-256, function count, completed/failed stage counts. Unknown external claims are not promoted or imported. No dependency replacement. Docker, Rizin and local Ghidra executables unavailable; upstream runtime unverified. Use python -m skell_vst_decompiler.verification reports --revenant /private/owned-fixture/report.json --sha256 <exact-hash> (omit optional flags for internal reconciliation). The verification stage emits a stable dependency key for future caching, not a persistent cache. Save CLI output outside the input reports directory.
