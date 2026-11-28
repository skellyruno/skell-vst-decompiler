# Multi-engine C++ class navigation

## Upstream evaluation

- [Ghidra](https://github.com/NationalSecurityAgency/ghidra), Apache-2.0: existing optional official headless backend, pinned owned-fixture CI. Its release-12.2 [RecoverClassesFromRTTIScript.java](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.2_build/Ghidra/Features/Decompiler/ghidra_scripts/RecoverClassesFromRTTIScript.java) is a prototype class-recovery script for RTTI, inheritance, constructors/destructors and inferred members. Use it separately in a fresh local Ghidra project when appropriate. It edits analysis metadata, not original image bytes; inferred members may be incomplete. We do not automatically run it or claim that its output has been validated.
- [Ghidra Cpp Class Analyzer](https://github.com/astrelsky/Ghidra-Cpp-Class-Analyzer), MIT: upstream is archived and explicitly recommends Ghidra's newer scripts. We did not install or copy the legacy extension; implemented a lightweight read-only MSVC x64 RTTI metadata scanner independently.
- [Cutter](https://github.com/rizinorg/cutter), GPL-3.0: independent GUI backed by [Rizin](https://github.com/rizinorg/rizin). Keep the external application separate. No Cutter code or GPL component is embedded. A JSON adapter compares analyst-exported function offsets against the original PE's unwind metadata. The adapter is tested on compiled fixture data, not on a live Rizin installation.

## Original class graph and targeted Ghidra bridge

```sh
python -m skell_vst_decompiler.classgraph '/private/TVB Rack V2.vst3' --class-keyword 'Module@dsp@voxbox'
python -m skell_vst_decompiler.classgraph '/private/TVB Rack V2.vst3' --class-keyword CompressorModule --exact-type '.?AVCompressorModule@dsp@voxbox@@' --table-rva 0x9273d0 --slots 3 4 5
```

The second command is an exact-build example. Inspect the first report before choosing the class, table and slots on other builds. Add `--ghidra-home /path/to/official/ghidra` to run the existing isolated headless bridge. No backend is required to generate the plan. Only selected addresses are exported; generated pseudocode remains local. No vendor executable is launched.

Metadata validation: MSVC x64 TypeDescriptor names, self-relative CompleteObjectLocator, class hierarchy descriptors and bounded base-class arrays, including member/virtual displacement, and file-backed executable-pointer candidates. Multiple inheritance and secondary subobjects are preserved. The scanner currently supports `.data`/`.rdata`, MSVC relative RTTI only. A contiguous pointer scan is **not** a proof of a vtable's exact length; tables may hit the 64-slot cap or include adjacent pointers. Unwind ranges are not always whole functions. Neither class names nor slot numbers prove effect behavior. Select known addresses, not entire protected or unrelated regions.

## Rizin function-index comparison

Export the function list from a separately installed Rizin/Cutter analysis (e.g. Rizin `aflj` JSON), normalize function entries to numeric `offset` virtual addresses, and put them in a local JSON object with these fields: `binary_sha256` (original source hash), `image_base` (integer analysis base), `functions` (array of objects with numeric `offset`). The analyst-supplied hash binds the document to the PE for comparison; it does not authenticate the producing engine. The importer rebases to RVA, deduplicates offsets, distinguishes exact unwind starts, interiors, no-record executable locations and non-file-backed addresses. No automated Rizin execution or actual Cutter GUI validation yet.

```sh
python -m skell_vst_decompiler.classgraph /private/FG-2A.epl --rizin-index local/rizin-functions.json
```

## Actual results and limits

See `reports/class_navigation_summary.json`: exact source fingerprints, 17 TVB DSP-module class records (18 tables), six VMR processor-template class records (six tables), 23 distinct selected method RVAs across the four binaries. TVB Suite EQ has an additional subobject at offset 336. All three VMR processor pairs inherit PluginProcessor and IPluginProcessor and expose distinct slot-8 candidates. This narrows the next comparison between paired variants, not a recovered complete gain law.

The owned freestanding C++ PE fixture was compiled with clang++ and lld-link. It recovers Filter, Base and Side, including the secondary table at offset 8, rejects corrupt self-relative locators, and verifies explicit slot planning and synthetic Rizin-style imports. Fixture source intentionally supplies a minimal type_info vtable symbol and `_fltused` for linker independence; never execute the fixture. No vendor source, raw tables, audio, or original executables are published. Local Ghidra and Rizin are not available; real vendor pseudocode, class-recovery script execution and Rizin output comparison remain unverified.
