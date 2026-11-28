# Full vocal headroom and wet-path refinement — 2026-11-26

Parent ab8a907817b327eb5f7037c907b90562bd453138. Reused the exact cached offline kit (13/13 checksums) and the existing 36-excerpt, 159.25-second private input manifest. All source SHA-256 fingerprints matched the manifest. Private input paths, identities, recordings and individual results remain outside Git.

## Complete the timed-out experiment

Completed four nine-input batches of the previous existing headroom harness, covering all seven color configurations (252 comparisons). The earlier -12 dB full-wet trim remained exactly a gain-only change: maximum absolute scaling error zero. Highest estimated peak +3.4376 -> -8.5624 dBFS; zero samples above full scale. Median raw RMS change relative to input -1.1479 dB, range -3.7159 to -0.0956 dB. No new production defaults, limiter or automatic gain compensation. This completes the previous subset result without treating overlapping excerpts as held-out performances. Four native binary digests matched; merged local report hash recorded in JSON.

## Presence wet-path trim

New lab-only adapter wraps the original fully wet PresenceEngine with an external wet-only gain and dry blend. Tested -4 dB wet trim at wet 0/.5/1 on all 36 recordings (108 mix cases). At zero trim, outputs match the original engine exactly at all three mix positions. Full-wet trim matches the baseline times the expected gain exactly; all tested blends match the dry plus trimmed wet calculation exactly. Dry endpoint remains unchanged.

| Wet | Worst original estimated peak dBFS | Worst trimmed peak dBFS | Trimmed median RMS change dB |
|---|---:|---:|---:|
| 0 | -1.3520 | -1.3520 | 0 |
| .5 | -.7796 | -3.4364 | -2.9774 |
| 1 | +2.3159 | -1.6841 | -3.7506 |

Zero over-scale samples in all tested trimmed cases. Fixed gain is a candidate setting, not a universal peak guarantee. At partial mix the wet-only trim necessarily changes dry/wet balance; the original algorithm and defaults remain untouched. First compile failed because the unqualified finite function was ambiguous with libc; qualified skell_lab::finite and rebuilt successfully.

## Existing contiguous oversampling real-vocal parity

Compared existing ColorContiguous2x/4x with ColorOversampled2x/4x at wet/trim pairs 1/0 dB, .5/-12 dB, 0/-12 dB. All 216 comparisons (108 per factor) were exactly sample-equal, including 72 exact aligned dry cases at 40 samples delay. The original headers were checked against Git blob identities; neither implementation changed in this batch.

Three paired alternating-order full-wet timing runs per implementation/factor/excerpt (432 runs). Median per-excerpt times and median paired reductions:

| Factor | Circular ms/audio-second | Contiguous ms/audio-second | Median paired reduction | Faster excerpts |
|---|---:|---:|---:|---:|
| 2x | 9.1412 | 9.0388 | 1.663% | 26/36 |
| 4x | 18.0065 | 17.4180 | 3.344% | 34/36 |

Small measured gains, not an order-of-magnitude optimization. Wall time includes preparation and native adapter, uncontrolled container load; not plugin host CPU. Keep contiguous implementations experimental; no production selection or algorithm change.

## CI failure and validation

The prior commit's real Ghidra job failed at apt installation before Ghidra ran: Microsoft Ubuntu 26.04 package feed HTTP 403, exit 100 ([run 45929614744](https://github.com/skellyruno/skell-vst-decompiler/actions/runs/45929614744)). Pinned that job to Ubuntu 24.04 and avoid apt if clang/lld-link already exist; retain required command checks, pinned Ghidra distribution hash and actual smoke tests. Hosted fix is unverified until CI runs. No main, release or manual job canceled.

31 targeted local unittest methods passed (28 prior + 3 new); new owned native fixture compiled with -O2 -Wall -Wextra -Werror and tested at 44.1/48/96 kHz for dry/trim/contiguous parity, rejection of invalid controls and mismatch. Exact tested source Git blobs matched. Real-vocal run used original 44.1 kHz. The new Python harness accepts --start/--count and writes only local reports; the full corpus was merged after all four batches and fingerprint identities verified.

Reproduce: `python benchmarks/owned_vocal_refinement.py --manifest /private/manifest.json --start 0 --count 9 --output /private/batch0.json` (repeat offsets 9/18/27). Requires NumPy, SciPy, SoundFile and native GCC. No private files needed for the new automated regression. All peaks estimated by 4x polyphase interpolation, not certified true peak. No real host, vendor equivalence, latency improvement, listening preference or production release claim. Vendor static research not rerun this batch; previous 854 unknown destinations, 90 boundary conflicts and 692 local candidates remain open.
