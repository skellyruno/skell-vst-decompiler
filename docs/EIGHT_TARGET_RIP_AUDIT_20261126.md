# Eight-target floating-point reference audit — 2026-11-26

Parent 34a7c5add83a60a1ab580f18829928d40f4bd47e. All eight exact binaries available locally, including FG-2A recovered and fingerprinted from the private split archive. Quick4 offline kit checksum manifest: 13/13 passed; no UI changes or JUCE build needed for this Python-only research.

New original tool rip_float_audit.py independently validates legacy SSE RIP-relative memory references against original instruction bytes and GNU/LLVM decoder destinations, and classifies the section access. It does not read vendor coefficient values. Owned PE fixture validates read-only and writable reads/writes, wrong fingerprint, invalid range, malformed and unsupported instructions. Five local targeted regression tests passed (two new, three existing); exact new and existing source/test Git hashes match. Full repository suite remains unverified locally.

47 selected metadata-bounded scopes, 71,030 bytes, 197 verified references, all reads from read-only sections, 20 excluded (18 FG-2A, 2 StandardCLIP). Zero matching references does not prove absence of DSP, and section flags do not prove runtime immutability. No VEX/EVEX, dynamic register operands, runtime routes or gain laws inferred.

| Target | Scopes | Verified | Excluded | Distinct targets | Shared across scopes |
|---|---:|---:|---:|---:|---:|
| StandardCLIP | 5 | 12 | 2 | 9 | 2 |
| Trackspacer | 6 | 47 | 0 | 21 | 5 |
| FG-2A | 8 | 70 | 18 | 43 | 6 |
| Panagement | 5 | 12 | 0 | 12 | 0 |
| DeeDoubler | 7 | 35 | 0 | 24 | 7 |
| VT-5 | 6 | 17 | 0 | 12 | 0 |
| SSL Stereo Image | 4 | 4 | 0 | 3 | 0 |
| MixHead | 6 | 0 | 0 | 0 | 0 |

FG-2A: one previously identified coefficient-generator candidate at 0xbf5290 has 40 verified sites, 24 distinct read-only locations, 2 excluded. This prioritizes that region for further investigation; optical compression/recovery not derived. Trackspacer: 34 sites in the earlier main processing candidate, 17 distinct; five shared across selected scopes. Band distribution/Q and attenuation law remain unresolved. StandardCLIP: two wrappers share two data locations; clipping and oversampling still unresolved. Panagement: references confined to the parameter-registration region in this selection, no active LFO routing claim. DeeDoubler: seven shared locations across selected scopes, no delay trajectory law established. VT-5: 13 scalar multiply references in dispatcher (9 single, 4 double), not an EQ coefficient mapping. SSL: four references, no stereo matrix recovered. MixHead: MachineHeadPlugInType and two coefficient-queue template class-name candidates located; six inspected ranges yield zero supported references. Not evidence of tape saturation.

Machine-readable bounded scope plan and counts: reports/native_scoped/eight_target_rip_audit_2026_11_26.json. Full local report SHA-256 recorded there. Re-run audit_scope on each exact input and listed start/length. No private source, vendor bytes, tables, pseudocode, audio, protected implementation, or production code uploaded. SkellCore and all shipped plugin states unchanged. Existing draft PR retained; do not merge until full CI is verified.
