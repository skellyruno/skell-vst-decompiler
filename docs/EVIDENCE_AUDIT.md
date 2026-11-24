# Evidence audit and class-entry coverage

Run `python -m skell_vst_decompiler.evidence_audit reports` against the committed reports. This read-only audit joins by exact source SHA-256, not names or coincident RVAs. It distinguishes entry coverage from unwind overlap; deduplicates repeated static call sites; isolates contradictory target claims; and ranks uncovered targets by distinct call-site count. The rank is a navigation aid, not a DSP importance ranking: frequently referenced imports and utilities may dominate.

Inputs are the existing report regions and class navigation summary. It rejects mismatched fingerprints, unplanned method addresses, duplicate evidence identities and call sites outside their reported intervals. Output is deterministic JSON. No new vendor binary analysis, pseudocode, runtime dispatch or production DSP change is asserted.

Follow-up: validate the report on the original privately stored source binaries when available, then use independently designed measurements to investigate dynamics, stereo and time-domain behavior. The existing Ghidra/Rizin integration remains separate; no upstream or third-party code is copied.
