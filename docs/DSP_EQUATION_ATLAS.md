# Skell DSP equation and code-location atlas

Overlapping local evidence, not an algorithm-completeness count. Calls are static decoded references, not proven runtime edges. Unmatched targets are unresolved in this catalog, not necessarily unknown functions. No vendor implementation or raw coefficient arrays.

**111 evidence records across 4 exact binary fingerprints.**

## FG-116.epl

SHA-256: `1cf796db09bc6ce3455d3fa3506614fa990374fc2f2642ff8fc9c40e626dfbf2` — 8 records.

### FG-116 clamped-state coefficient and bounds setup

- **RVA:** `0x15e732–0x15e88c` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg116_clamped_state_setup`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

Loads coefficients a, k1, k0 at offsets 0x160/168/170, previous state at channel record +0x60, and signed clamp bounds from file-backed constants.

Static direct call references:

- `0x15e7bf` → `0x6f840`: not covered in catalog

### FG-116 clamped two-output integrator and branch-dependent coefficient

- **RVA:** `0x15eaa1–0x15eb40` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg116_clamped_integrator`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

Finite input/state: c=clamp(s,-0.053088,0.046774); d=a*(x-s); q=c+d; s_next=c+2*d; flag=(s!=c); k=(1-flag)*k0+flag*k1. q, flag, and k enter separate scratch arrays. No physical circuit or knob interpretation asserted.

### FG-116 minimum envelope of selected coefficients

- **RVA:** `0x15eb40–0x15ec87` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg116_selected_retention`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

The branch-selected k stream feeds k_s=min(k,k+a_r*(k_s_prev-k)), using retention field 0x178 and channel state +0x58.

### FG-116 variable-coefficient state and residual output

- **RVA:** `0x15ec87–0x15edb0` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg116_variable_integrator`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

The smoothed k stream feeds an independent state: e=x-v; v_next=v+k_s*e. Writes residual e to scratch and stores v at channel state +0x68. Local signal path, not a complete compressor gain equation.

### Minimum-constrained envelope

- **RVA:** `0x161880–0x161998` (end exclusive)
- **Evidence:** `vmr_control_streams.json::fg116_min_envelope`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

For finite inputs, s=min(x,x+a*(s_prev-x)); s stored to output and state. For 0<=a<=1 this captures decreases immediately and smooths increases. Input buffer semantics remain unknown.

### Fixed input scalar smoothing

- **RVA:** `0x1619a0–0x161be1` (end exclusive)
- **Evidence:** `vmr_control_streams.json::fg116_input_slew`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

g += 0.0025*(target-g); y=x*g. Initialization branch sets g=target. This is a local scalar gain stage, not the compression gain computer.

### Shared slot 4/5 processing candidate

- **RVA:** `0x1619a0–0x162418` (end exclusive)
- **Evidence:** `vmr_effect_paths.json::effect_candidate`
- **Confidence:** candidate / confidence not explicitly recorded

Smoothed scalar gain multiplication: g+=alpha*(target-g); y=x*g; per-lane gain state written back.

Static direct call references:

- `0x161c24` → `0xcea1f4`: not covered in catalog
- `0x161c3c` → `0xcea1f4`: not covered in catalog
- `0x161c46` → `0x15d8a0`: not covered in catalog
- `0x161c80` → `0xcea1f4`: not covered in catalog
- `0x161c98` → `0xcea1f4`: not covered in catalog
- `0x161ca2` → `0x15d030`: not covered in catalog
- `0x161cda` → `0xcea1f4`: not covered in catalog
- `0x161cf4` → `0xcea1f4`: not covered in catalog
- `0x161d42` → `0x161880`: `vmr_control_streams.json::fg116_min_envelope`
- `0x161d77` → `0xcea1f4`: not covered in catalog
- `0x161d91` → `0xcea1f4`: not covered in catalog
- `0x161da5` → `0x15ddd0`: not covered in catalog
- `0x161dd6` → `0xcea1f4`: not covered in catalog
- `0x161df0` → `0xcea1f4`: not covered in catalog
- `0x161e04` → `0x15d4a0`: not covered in catalog
- `0x161e1d` → `0x6f7c0`: not covered in catalog
- `0x161e3b` → `0x6f840`: not covered in catalog
- `0x161e5a` → `0x6f820`: not covered in catalog
- `0x161e69` → `0x163950`: not covered in catalog
- `0x161ead` → `0x6f8a0`: not covered in catalog
- `0x162153` → `0xcea1f4`: not covered in catalog
- `0x16216b` → `0xcea1f4`: not covered in catalog
- `0x162175` → `0x15e670`: not covered in catalog
- `0x1623da` → `0x6f860`: not covered in catalog

### Candidate envelope caller

- **RVA:** `0x161ca7–0x161d47` (end exclusive)
- **Evidence:** `vmr_control_streams.json::fg116_envelope_call`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

The scalar retention argument comes from the object at r15+0x10; output scratch rbp+0x60 and persistent state rsi+0x70. Physical units and host knob mapping unverified.

## FG-2A.epl

SHA-256: `6b365ee15dbb94efb9d97b76923445f4ad4f3740194e21363cd9ffbe8df8d573` — 33 records.

### Vector sum dispatch

- **RVA:** `0x6f860–0x6f872` (end exclusive)
- **Evidence:** `vmr_control_streams.json::fg2a_sum_dispatch`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

Seven inspected slots resolve to four entry points. Selected runtime slot unknown; all four candidate entries lead to vector addition.

### FG-2A symmetric clipping candidate

- **RVA:** `0x7128a–0x712c3` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_symmetric_clip`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

Inspected scalar helper: dst=clamp(src,-limit,+limit), finite limit >= 0.

### In-place scalar multiply

- **RVA:** `0x7173d–0x7174e` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_helper_6f7e0`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

dst*=scalar for inspected first dispatch slot; other slots not established.

### FG-2A scalar addition candidate

- **RVA:** `0x71c09–0x71c18` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_scalar_offset`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

Inspected scalar helper: dst=src+offset.

### Out-of-place scalar multiply

- **RVA:** `0x721a1–0x721b0` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_helper_6f820`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

dst=src*scalar for inspected first dispatch slot; other slots not established.

### In-place vector sum

- **RVA:** `0x7277b–0x7278d` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_helper_6f840`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

dst+=src for inspected first dispatch slot; other slots not established.

### Vector sum scalar and packed arithmetic

- **RVA:** `0x72b60–0x72d40` (end exclusive)
- **Evidence:** `vmr_control_streams.json::fg2a_sum_scalar`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

Scalar and packed paths sum src1+src2 into output.

### Four slots share addition wrapper

- **RVA:** `0x72d40–0x72d78` (end exclusive)
- **Evidence:** `vmr_control_streams.json::fg2a_sum_bridge`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

Wrapper calls vector arithmetic helper.

### Two wide-vector sum candidates

- **RVA:** `0x72d80–0x73025` (end exclusive)
- **Evidence:** `vmr_control_streams.json::fg2a_sum_avx`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

Both AVX candidate paths also perform addition. Not a distinct nonlinear compression algorithm.

### FG-2A vector difference candidate

- **RVA:** `0x730a1–0x730b3` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_subtract`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

Inspected scalar helper: dst=second-first.

### Vector multiply

- **RVA:** `0x73571–0x73583` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_helper_6f8a0`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

dst=src1*src2 for inspected first dispatch slot; other slots not established.

### FG-2A vector division candidate

- **RVA:** `0x739fa–0x73a19` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_division`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

Inspected scalar helper: dst=second/first for finite nonzero denominator. Exceptional denominator handling is outside this equation.

### Scalar/packed sum helper

- **RVA:** `0x74d90–0x74e68` (end exclusive)
- **Evidence:** `vmr_control_streams.json::fg2a_sum_helper`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

Addition verified in scalar and packed instructions.

### FG-2A square dispatcher and seven forwarding entries

- **RVA:** `0x75f40–0x76030` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_square_dispatch`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

Seven explicit dispatch slots lead through forwarding stubs to four file-backed square candidate routines.

### FG-2A scalar, SSE, AVX square arithmetic

- **RVA:** `0x76040–0x76a90` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_square_kernels`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

All four candidate entry routines contain scalar or packed self-multiplication; the scalar body explicitly stores x*x. No claim of runtime dispatch selection.

Static direct call references:

- `0x76a38` → `0xd38410`: not covered in catalog
- `0x76a5e` → `0xd38410`: not covered in catalog
- `0x76a87` → `0xd38410`: not covered in catalog

### FG-2A local biased rational transform

- **RVA:** `0x142110–0x142335` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_rational_stage`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

On the inspected scalar dispatch path for finite input/nonzero denominator/nonnegative limit: u=x+offset_in; numerator=A*u^3+B*u; denominator=u^2+C; dst=clamp(numerator/denominator,-limit,limit)+offset_out. Six coefficient fields in argument record at +0/+8/+0x10/+0x20/+0x28/+0x30. Runtime coefficient origins and dispatch unverified.

Static direct call references:

- `0x14216c` → `0x6f800`: not covered in catalog
- `0x142180` → `0x75f40`: `vmr_nonlinear_paths.json::fg2a_square_dispatch`
- `0x14219b` → `0x6f8a0`: not covered in catalog
- `0x1421b5` → `0x6f820`: not covered in catalog
- `0x1422c8` → `0x6f800`: not covered in catalog
- `0x1422e5` → `0x6f8c0`: not covered in catalog
- `0x142300` → `0x6f7c0`: not covered in catalog
- `0x142317` → `0x6f800`: not covered in catalog

### FG-2A initializer and processing subobject link

- **RVA:** `0x142340–0x14239f` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_initializer_object`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

Setup calls coefficient initializer with parent subobject +0x1360; a separate subobject at +0x590 has a different initializer.

Static direct call references:

- `0x142358` → `0x19b970`: not covered in catalog
- `0x14237b` → `0x142c20`: not covered in catalog
- `0x142387` → `0x1423a0`: `vmr_fg2a_coefficient_provenance.json::fg2a_weight_initializer`

### FG-2A nine polynomial calibration weights

- **RVA:** `0x1423a0–0x1425b7` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_weight_initializer`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

Nine scalar weights follow signed exp(ln(10)*0.05*d), equivalently signed 10^(d/20), with file-backed dB calibrations. Actual runtime updates not excluded.

Static direct call references:

- `0x142409` → `0xd38e54`: not covered in catalog
- `0x142435` → `0xd38e54`: not covered in catalog
- `0x14246f` → `0xd38e54`: not covered in catalog
- `0x1424a0` → `0xd38e54`: not covered in catalog
- `0x1424cc` → `0xd38e54`: not covered in catalog
- `0x1424fd` → `0xd38e54`: not covered in catalog
- `0x14252e` → `0xd38e54`: not covered in catalog
- `0x14255f` → `0xd38e54`: not covered in catalog
- `0x142587` → `0xd38e54`: not covered in catalog

### FG-2A logarithmic calibration base

- **RVA:** `0x1425b7–0x1425ee` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_weight_base`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

A static initialization path computes ln(10)*0.05 and writes it to shared calibration scalar 0x10364d0.

Static direct call references:

- `0x1425be` → `0xd37ca8`: not covered in catalog
- `0x1425cf` → `0xd38e3c`: not covered in catalog
- `0x1425e7` → `0xd37c48`: not covered in catalog

### FG-2A coefficient base and channel count

- **RVA:** `0x14d5bd–0x14d61c` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_processing_context`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

RBX is the supplied subobject pointer; the processing loop copies two streams and uses twice the per-stream sample count for vector operations.

Static direct call references:

- `0x14d610` → `0x6f740`: not covered in catalog

### FG-2A signed curve constant setup

- **RVA:** `0x14d748–0x14d76d` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_curve_sign_setup`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

Loads +1, -1 and zero used for sign and absolute magnitude in the piecewise branch.

### FG-2A signed biased piecewise quadratic and plateau

- **RVA:** `0x14d9c1–0x14da5e` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_signed_curve`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

u=x+bias; p=abs(u); F(p)=p if p<=lo, plateau if p>hi and p>lo, A*p*p+B*p+C otherwise; v=sign(u)*F(p)-offset (sign(0)=+1). Finite values only. Exact runtime coefficients and physical purpose unknown.

### FG-2A even-power nonlinear polynomial candidate

- **RVA:** `0x14da5e–0x14db2d` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_even_power_chain`
- **Confidence:** instruction-verified call/argument chain with inspected helper candidates; runtime selector unverified

On the inspected scalar helper dispatch paths: v2=v*v; v4=v2*v2; v6=v4*v2; v8=v4*v4; p=A*v4+B*v6+C*v8. Coefficients are fields 0x560,0x568,0x578. All seven square slots checked; scalar candidate multiply/scale/add semantics established, not every alternative helper slot. Not claimed to be the final gain computer.

Static direct call references:

- `0x14da6f` → `0x75f40`: `vmr_nonlinear_paths.json::fg2a_square_dispatch`
- `0x14da85` → `0x75f40`: `vmr_nonlinear_paths.json::fg2a_square_dispatch`
- `0x14daa2` → `0x6f8a0`: not covered in catalog
- `0x14dab6` → `0x75f40`: `vmr_nonlinear_paths.json::fg2a_square_dispatch`
- `0x14dacb` → `0x6f7e0`: not covered in catalog
- `0x14dae2` → `0x6f7e0`: not covered in catalog
- `0x14daf6` → `0x6f840`: not covered in catalog
- `0x14db14` → `0x6f820`: not covered in catalog
- `0x14db28` → `0x6f840`: not covered in catalog

### FG-2A nine initialized weight read endpoints

- **RVA:** `0x14dabb–0x14de64` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_weight_consumers`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

All nine initialized weight fields are read from the linked subobject in this candidate. The last endpoint (0x580) scales the fourth-power scratch stream. A matching read is not proof that every path is executed in a live plugin.

Static direct call references:

- `0x14dacb` → `0x6f7e0`: not covered in catalog
- `0x14dae2` → `0x6f7e0`: not covered in catalog
- `0x14daf6` → `0x6f840`: not covered in catalog
- `0x14db14` → `0x6f820`: not covered in catalog
- `0x14db28` → `0x6f840`: not covered in catalog
- `0x14dc45` → `0x6f820`: not covered in catalog
- `0x14dc59` → `0x6f840`: not covered in catalog
- `0x14dc74` → `0x142110`: `vmr_fg2a_coefficient_provenance.json::fg2a_rational_stage`
- `0x14dd86` → `0x6f7e0`: not covered in catalog
- `0x14dda3` → `0x6f8a0`: not covered in catalog
- `0x14ddc0` → `0x6f8a0`: not covered in catalog
- `0x14dddb` → `0x6f8a0`: not covered in catalog
- `0x14ddf0` → `0x6f7e0`: not covered in catalog
- `0x14de07` → `0x6f7e0`: not covered in catalog
- `0x14de1b` → `0x6f840`: not covered in catalog
- `0x14de32` → `0x6f7e0`: not covered in catalog
- `0x14de48` → `0x6f840`: not covered in catalog
- `0x14de5f` → `0x6f7e0`: not covered in catalog

### FG-2A post-polynomial DF2T filter

- **RVA:** `0x14db50–0x14dbbb` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::fg2a_biquad_after_polynomial`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

Standard double DF2T recurrence follows the even-power sum scratch; coefficients 0x360/368/370/380/388. Frequency response, actual runtime values and ultimate role remain unknown.

### FG-2A two rational transform callsites

- **RVA:** `0x14dc2c–0x14dc79` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_rational_consumers`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

The filtered even-order sum is combined with a weighted squared term, then passed to a rational transform with parameter record +0x238. This verifies a second-order contribution in addition to the previous fourth/sixth/eighth-order polynomial.

Static direct call references:

- `0x14dc45` → `0x6f820`: not covered in catalog
- `0x14dc59` → `0x6f840`: not covered in catalog
- `0x14dc74` → `0x142110`: `vmr_fg2a_coefficient_provenance.json::fg2a_rational_stage`

### FG-2A additional stereo DF2T bank

- **RVA:** `0x14dc90–0x14dd74` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_second_filter`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

Two independent DF2T state pairs share coefficients at 0x3d0/3d8/3e0/3f0/3f8. Standard y=b0*x+z1, z1_next=b1*x-a1*y+z2, z2_next=b2*x-a2*y. Frequency calibration unresolved.

### FG-2A odd-power parallel branch

- **RVA:** `0x14dd74–0x14de64` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_odd_order_terms`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

Previously computed v^2 combines with v to form v^3, v^5, v^7. The inspected vector paths scale and sum v^3/v^7, then scale the sum and add to a filtered branch. v^5 is formed but its final use is not established here.

Static direct call references:

- `0x14dd86` → `0x6f7e0`: not covered in catalog
- `0x14dda3` → `0x6f8a0`: not covered in catalog
- `0x14ddc0` → `0x6f8a0`: not covered in catalog
- `0x14dddb` → `0x6f8a0`: not covered in catalog
- `0x14ddf0` → `0x6f7e0`: not covered in catalog
- `0x14de07` → `0x6f7e0`: not covered in catalog
- `0x14de1b` → `0x6f840`: not covered in catalog
- `0x14de32` → `0x6f7e0`: not covered in catalog
- `0x14de48` → `0x6f840`: not covered in catalog
- `0x14de5f` → `0x6f7e0`: not covered in catalog

### FG-2A later branch merge and second rational transform

- **RVA:** `0x14e04e–0x14e0ae` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_branch_merge`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

A second rational transform uses record +0x270. Its output is differenced against the preceding stream and added into another scratch branch on the inspected helper paths. This is not the final audio gain law.

Static direct call references:

- `0x14e05d` → `0x6f840`: not covered in catalog
- `0x14e078` → `0x142110`: `vmr_fg2a_coefficient_provenance.json::fg2a_rational_stage`
- `0x14e093` → `0x6f880`: not covered in catalog
- `0x14e0a9` → `0x6f840`: not covered in catalog

### FG-2A candidate local clipping and output handoff

- **RVA:** `0x14e1b6–0x14e2ab` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_local_output_merge`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

Inspected scalar candidates clamp a local filtered branch, add the saved input scratch stream, copy two buffers, and pass a context to 0x14f340. That downstream routine and final plugin output remain unresolved.

Static direct call references:

- `0x14e1c8` → `0x6f7c0`: not covered in catalog
- `0x14e1dc` → `0x6f840`: not covered in catalog
- `0x14e22c` → `0x6f740`: not covered in catalog
- `0x14e279` → `0xd38dc4`: not covered in catalog
- `0x14e29a` → `0xd38dc4`: not covered in catalog
- `0x14e2a6` → `0x14f340`: not covered in catalog

### Dual scalar gain and parallel sum

- **RVA:** `0x155960–0x155c3f` (end exclusive)
- **Evidence:** `vmr_control_streams.json::fg2a_dual_slew`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

Two independent scalar gain ramps per channel use g+=.0025*(target-g), then sum two weighted scratch streams. Verified vector-add candidates below; identities of the two streams and complete gain law unknown.

### Shared slot 4/5 processing candidate

- **RVA:** `0x156b20–0x156ffb` (end exclusive)
- **Evidence:** `vmr_effect_paths.json::effect_candidate`
- **Confidence:** candidate / confidence not explicitly recorded

Two distinct stereo double-precision first-order filter passes: y=b0*x+z; z_next=b1*x-a1*y. Coefficient meanings and full optical gain law unknown.

Static direct call references:

- `0x156c30` → `0xd38dc4`: not covered in catalog
- `0x156c4b` → `0xd38dc4`: not covered in catalog
- `0x156c55` → `0x150870`: not covered in catalog
- `0x156ce8` → `0x1535f0`: not covered in catalog
- `0x156d23` → `0xd38dc4`: not covered in catalog
- `0x156d3b` → `0xd38dc4`: not covered in catalog
- `0x156d45` → `0x14cff0`: not covered in catalog
- `0x156d5a` → `0xd38dc4`: not covered in catalog
- `0x156d73` → `0xd38dc4`: not covered in catalog
- `0x156f2d` → `0xd38dc4`: not covered in catalog
- `0x156f45` → `0xd38dc4`: not covered in catalog
- `0x156f4f` → `0x14d590`: not covered in catalog
- `0x156fb9` → `0x155960`: `vmr_control_streams.json::fg2a_dual_slew`
- `0x156fd1` → `0x141e60`: not covered in catalog

### FG-2A processing subobject argument

- **RVA:** `0x156f00–0x156f54` (end exclusive)
- **Evidence:** `vmr_fg2a_coefficient_provenance.json::fg2a_processing_object`
- **Confidence:** exact-build static evidence; runtime dispatch unverified

The processing caller passes parent subobject +0x1360 through the first context slot to 0x14d590.

Static direct call references:

- `0x156f2d` → `0xd38dc4`: not covered in catalog
- `0x156f45` → `0xd38dc4`: not covered in catalog
- `0x156f4f` → `0x14d590`: not covered in catalog

## FG-Stress.epl

SHA-256: `2509a6f3480481feb15a0fde97abcb4acccfc6fc936f55f5e8c88b7c98edcd26` — 6 records.

### Shared slot 4/5 processing candidate

- **RVA:** `0x162790–0x1638b6` (end exclusive)
- **Evidence:** `vmr_effect_paths.json::effect_candidate`
- **Confidence:** candidate / confidence not explicitly recorded

Linked peak recurrence P=max(p,p+a*(P_prev-p)); p=max(abs(L),abs(R)). Then two bounded threshold-relative control calculations; their full effect not yet established.

Static direct call references:

- `0x16291d` → `0xd0c514`: not covered in catalog
- `0x162946` → `0xd0c514`: not covered in catalog
- `0x162950` → `0x15b300`: not covered in catalog
- `0x162997` → `0xd0c514`: not covered in catalog
- `0x1629c4` → `0xd0c514`: not covered in catalog
- `0x162a88` → `0xd0c514`: not covered in catalog
- `0x162ab5` → `0xd0c514`: not covered in catalog
- `0x162b46` → `0x6f9a0`: not covered in catalog
- `0x162b9a` → `0xd0c514`: not covered in catalog
- `0x162bc7` → `0xd0c514`: not covered in catalog
- `0x162c66` → `0x6f9a0`: not covered in catalog
- `0x162c81` → `0x6f860`: not covered in catalog
- `0x162c9c` → `0x808c0`: not covered in catalog
- `0x162cad` → `0x6f8a0`: not covered in catalog
- `0x162ce3` → `0x6f860`: not covered in catalog
- `0x162f69` → `0x6f840`: not covered in catalog
- `0x162f84` → `0x6f900`: not covered in catalog
- `0x162fe6` → `0xd0c514`: not covered in catalog
- `0x163010` → `0xd0c514`: not covered in catalog
- `0x16301a` → `0x15cd20`: not covered in catalog
- `0x163097` → `0x6f860`: not covered in catalog
- `0x1632f4` → `0x6f840`: not covered in catalog
- `0x163335` → `0x6f8a0`: not covered in catalog
- `0x163343` → `0x6f9c0`: not covered in catalog
- `0x16335e` → `0x6f800`: not covered in catalog
- `0x1633f1` → `0x15d420`: not covered in catalog
- `0x16341a` → `0xd0c514`: not covered in catalog
- `0x16355b` → `0xd0c514`: not covered in catalog
- `0x163577` → `0xd0c514`: not covered in catalog
- `0x163639` → `0xd0c514`: not covered in catalog
- `0x163655` → `0xd0c514`: not covered in catalog
- `0x163739` → `0x15c0f0`: not covered in catalog
- `0x163757` → `0x6fa00`: not covered in catalog
- `0x163775` → `0x6fa00`: not covered in catalog
- `0x1637d1` → `0x6f9e0`: not covered in catalog
- `0x16381a` → `0x6f9e0`: not covered in catalog
- `0x16387d` → `0xd0b3f8`: not covered in catalog
- `0x163893` → `0xd0c58c`: not covered in catalog
- `0x1638ac` → `0xd0b398`: not covered in catalog

### Control range constants

- **RVA:** `0x163031–0x16304e` (end exclusive)
- **Evidence:** `vmr_control_streams.json::stress_bounds_setup`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

Local path establishes zero and one clamp boundaries; absolute-value mask and slope checked at consuming sites.

### FG-Stress affine/quadratic/identity nonlinear branch

- **RVA:** `0x163270–0x1632f9` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::stress_piecewise`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

Ordered finite thresholds lo<=hi: F(x)=x for x>=hi, A*x+B for x<lo, C*x*x+D*x+E otherwise. Coefficients at object offsets 0xd8..0xf8; continuity, target parameter mapping and gain-law role unknown.

Static direct call references:

- `0x1632f4` → `0x6f840`: not covered in catalog

### FG-Stress nonlinear scratch flow into downstream effect routine

- **RVA:** `0x163300–0x1633f6` (end exclusive)
- **Evidence:** `vmr_nonlinear_paths.json::stress_curve_caller`
- **Confidence:** instruction-verified local arithmetic; runtime dispatch unverified

The transformed channel stream is consumed by subsequent vector calls and is passed alongside derived scratch buffers to the downstream candidate at 0x15d420. Its complete effect on output has not been proven.

Static direct call references:

- `0x163335` → `0x6f8a0`: not covered in catalog
- `0x163343` → `0x6f9c0`: not covered in catalog
- `0x16335e` → `0x6f800`: not covered in catalog
- `0x1633f1` → `0x15d420`: not covered in catalog

### Coupled bounded detector controls

- **RVA:** `0x163442–0x163521` (end exclusive)
- **Evidence:** `vmr_control_streams.json::stress_control_pair`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

For finite P, U=clamp(130*(P-T1),0,1); V=(1-U)*clamp(130*(P-T0),0,1). These are bounded scratch control streams, not established audio gain.

### Control-stream history stores

- **RVA:** `0x1637d6–0x163866` (end exclusive)
- **Evidence:** `vmr_control_streams.json::stress_control_history`
- **Confidence:** instruction-verified local arithmetic; runtime selection unverified

The same bounded streams feed reduction/summary calls and 1024-position circular histories. The summary operation and whether these streams also affect audio remain unresolved.

## TVB Rack V2.vst3

SHA-256: `cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9` — 64 records.

### Four named host lookup slots

- **RVA:** `0x33c7e4–0x33c86f` (end exclusive)
- **Evidence:** `tvb_coloration.json::parameter_lookup`
- **Confidence:** instruction-verified handle lookup; DSP binding unresolved

Names resolve through common lookup helpers to literal pointer slots. This does not establish the destination compressor fields or setter path.

### Primary FET input calibration, threshold and output coupling

- **RVA:** `0x342fa8–0x3431c3` (end exclusive)
- **Evidence:** `tvb_extended_dsp.json::compound_gain`
- **Confidence:** instruction-verified local algebra/structure; runtime unverified

Finite inputs: z=lerp(input_curve,clamp(threshold+59,0,59))+input_db; I=clamp(z,-12,24); e=z-I; T=clamp(-e,-72,0); O=clamp(lerp(output_curve,clamp(cla_output+59,0,59))+output_db+e,-120,24). If threshold or CLA output <= -59.95, O=-120. Fields 0x17c=input, 0x150=threshold, 0x174=output; makeup and auto makeup zeroed. CLA default -18 if absent. Curves are file-backed and fingerprinted, not exported.

### Primary threshold, input and output coupling

- **RVA:** `0x342fa8–0x3431b3` (end exclusive)
- **Evidence:** `tvb_parameter_mapping.json::primary_threshold_drive`
- **Confidence:** instruction-verified endpoints, intermediate equations incomplete

Primary threshold and CLA output feed conditional/table-based gain calculation with input and output parameters; destinations include threshold 0x150, field 0x174 and field 0x17c. Not simple one-to-one knob mapping.

### Processing path assigns mode 1 and mode 2

- **RVA:** `0x343ea2–0x343eb0` (end exclusive)
- **Evidence:** `tvb_parameter_mapping.json::mode_assignments`
- **Confidence:** instruction-verified mode writes for this path

Writes numeric mode 1 to first instance field 0x184, mode 2 to second. Does not prove all host paths use fixed modes.

### Optical detector and compression amount bindings

- **RVA:** `0x344129–0x3441b4` (end exclusive)
- **Evidence:** `tvb_parameter_mapping.json::secondary_optical`
- **Confidence:** instruction-verified endpoints

fx_comp2_la2a_limit -> 0x188; fx_comp2_la2a_hifreq -> 0x18c; fx_comp2_compress -> 0x190, after default and range logic.

### Two constructed compressor instances

- **RVA:** `0x34bd12–0x34bd2b` (end exclusive)
- **Evidence:** `tvb_parameter_mapping.json::compressor_objects`
- **Confidence:** instruction-verified object base chain

Parent + 0x1e90 + child offsets 0x324d8 or 0x33500. Both use same verified compressor constructor/vtable.

### 24-band detector/output EQ handoff in 32-frame chunks

- **RVA:** `0x35bb80–0x35bc6c` (end exclusive)
- **Evidence:** `tvb_extended_dsp.json::eq_schedule`
- **Confidence:** instruction-verified local algebra/structure; runtime unverified

For each <=32-frame chunk, call detector then transfer 24 per-band signed gain adjustments to audio EQ before processing the chunk.

### Suite EQ mono TPT sample consumer

- **RVA:** `0x5a43e0–0x5a4466` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::eq_consumer`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

v3=x-s2; v1=a1*s1+a2*v3; v2=s2+a2*s1+a3*v3; s1_next=2*v1-s1; s2_next=2*v2-s2; y=m0*x+m1*v1+m2*v2. Mono TPT branch; other cascades remain.

### Dynamic EQ bandpass coefficient and detector recurrences

- **RVA:** `0x5a5090–0x5a5d70` (end exclusive)
- **Evidence:** `tvb_extended_dsp.json::eq_detector`
- **Confidence:** instruction-verified local algebra/structure; runtime unverified

TPT bandpass branch: g=tan(pi*clamp(f,1,0.49*Fs)/Fs), k=1/max(Q,.025), a1=1/(1+g*(g+k)), a2=g*a1,a3=g*a2; output=k*v1. Fast and slow absolute envelopes. Signed adjustment = range*clamp((L-T)/clamp(6+0.5*abs(range),6,24),0,1); fixed threshold or slow-envelope dB+3. Fast retention is frequency/control-dependent; slow retention exp(-1/(2*Fs)). 24 records of 0x168 bytes. Other detector routing branches exist.

### Eight-way TPT coefficient builder

- **RVA:** `0x5a5ef0–0x5a6117` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::eq_coefficients`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

A=10^(gain_dB/40); g=tan(pi*f/Fs), k=1/max(Q,.025). Numeric modes 0 highpass, 1 bell (k=k/A), 2 low shelf (g=g/sqrt(A)), 3 high shelf (g=g*sqrt(A)), 4 notch, 5 bandpass, 6 lowpass, 7 allpass. Coefficient mixer and integrator math documented in report; GUI mapping not established.

### De-esser complementary two-section crossover

- **RVA:** `0x5b6b20–0x5b6c2a` (end exclusive)
- **Evidence:** `tvb_extended_dsp.json::deess_crossover`
- **Confidence:** instruction-verified local algebra/structure; runtime unverified

Two TPT lowpass sections with shared g,k. low=LP2(LP1(x)); high=HP1+LP1-k*BP1-low. Sum is allpass1, not sample-identical dry.

### Gate high-pass and stereo-linked absolute envelope

- **RVA:** `0x5c99ac–0x5c9a47` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::gate_detector`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

hp=a*(x-x_prev+hp_prev); p=max_channel(abs(hp)); E+=alpha_attack_or_release*(p-E); level=max(-120,20log10(E)). Detector filtered, main audio multiplied separately.

### Gate hysteresis, hold and gain smoothing

- **RVA:** `0x5c9a47–0x5c9b18` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::gate_hold`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

Open when detector level > T, reload hold; below close threshold decrement hold then close. When closed, gain_dB=max(floor,(level-T)*(ratio-1)); when open, 0 dB. Linear gain uses separate rising/falling smoothing. Close threshold optionally T-4 dB; native setup mapping and runtime not fully established.

### FET filter coefficient row selection

- **RVA:** `0x5cf350–0x5cf468` (end exclusive)
- **Evidence:** `tvb_coloration.json::nearest_rate`
- **Confidence:** instruction-verified structure

Choose row by minimum absolute difference from six rate anchors; strict comparisons preserve earlier index at ties. Actual host behavior not measured.

### Continuous adjacent detector selection

- **RVA:** `0x5cfcb8–0x5cfd67` (end exclusive)
- **Evidence:** `tvb_detector_mapping.json::detector_morph`
- **Confidence:** instruction-verified for valid 0..100 inputs

Choose adjacent detector groups at anchors 0,20,40,60,80,100; interpolate with t=(v-lo)/(hi-lo). Source field 0x18c. Above 100 the code instead uses index 0 and weight 0; do not infer out-of-range behavior as clamping.

### Nonlinear target-coordinate calibration

- **RVA:** `0x5cfd61–0x5cfe3f` (end exclusive)
- **Evidence:** `tvb_detector_mapping.json::target_calibration`
- **Confidence:** instruction-verified structure

Object field 0x190 is clamped to 0..100, then interpolated through a five-point decreasing offset curve. Raw values withheld; curve coordinates 0,36,50,75,100.

### Rate-dependent adaptive coefficients

- **RVA:** `0x5cfe3f–0x5cffd9` (end exclusive)
- **Evidence:** `tvb_detector_mapping.json::rate_setup`
- **Confidence:** instruction-verified structure

Two file-backed 14-word calibration records feed the setup. For positive F, step=1000/F; rate-dependent exponentials produce peak decay and two one-pole update coefficients. The attack increment factor is B*step/max(T,0.01); the reciprocal gain-dependence factor is 1/max(D,0.5). Record selection is controlled by a flag. F units inferred from sample-rate-like source field.

### Attack/release coefficient construction

- **RVA:** `0x5d0379–0x5d04f7` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::attack_release_setup`
- **Confidence:** instruction-verified

mode 0 single alpha=1-exp(-1/(0.001*t*F)); auxiliary recovery coefficients use 0.08*F, 0.30*F, 1.50*F; mode 0 peak time uses 15 ms

### Independent input/output gain ramps and dry blend

- **RVA:** `0x5d052e–0x5d07b5` (end exclusive)
- **Evidence:** `tvb_extended_dsp.json::gain_consumers`
- **Confidence:** instruction-verified local algebra/structure; runtime unverified

Field 0x17c is converted to a smoothed linear input multiplier, field 0x174 to output gain; db<=-100 maps to zero, else 10^(db/20).

### Input gain and channel iteration

- **RVA:** `0x5d0740–0x5d07bf` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::input_detector`
- **Confidence:** instruction-verified

x_g = x * input_gain; store x_g; iterate channels

### Six groups of four detector biquads

- **RVA:** `0x5d07bf–0x5d117e` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::mode2_filter_bank`
- **Confidence:** instruction-verified-structure

six group inputs restart at x_g; p_j=max_c(w_j*abs(group_j(x_g))); each group has four two-state sections

### Linked peak / level detector

- **RVA:** `0x5d1246–0x5d12ef` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::peak_level`
- **Confidence:** instruction-verified

p=max_c(abs(filtered x_g)); e=p if p>e_old else e_old+a*(p-e_old); L=max(-90,20*log10(e)) for e>0, otherwise -90

### Alternate gain curve and adaptive state

- **RVA:** `0x5d12f9–0x5d15b4` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::mode1_custom`
- **Confidence:** partial

table interpolation and two coupled state updates; complete curve and control mapping unresolved

### Ratio-indexed interpolation across curve rows

- **RVA:** `0x5d1342–0x5d14aa` (end exclusive)
- **Evidence:** `tvb_curve_provenance.json::mode1_curve_blend`
- **Confidence:** instruction-verified structure

Special selector uses row 4. Ordinary selector scales row 0 below anchor 4, interpolates adjacent rows between anchors 4, 8, 12, 20, and selects row 3 above 20; the source field and UI semantics remain unverified.

### Mode 1 nonlinear target and coupled recovery

- **RVA:** `0x5d14aa–0x5d15af` (end exclusive)
- **Evidence:** `tvb_curve_provenance.json::mode1_history_release`
- **Confidence:** instruction-verified structure

Nonlinear target uses exp and optional pow. Primary state Q at 0x210 rises using attack coefficient and falls with coefficient b/(1+k*H). Secondary history H at 0x214 smooths a transformed log1p output, which is coupled back into target and release. Full parameter scaling unresolved.

### Six parallel peak and power states

- **RVA:** `0x5d15be–0x5d172e` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::mode2_envelopes`
- **Confidence:** instruction-verified

P_j=max(decay*P_j,p_j); E_j=E_j+alpha*(p_j^2-E_j), j=0..5

### Two-stage interpolation of peak and power in logarithmic units

- **RVA:** `0x5d172e–0x5d18d6` (end exclusive)
- **Evidence:** `tvb_detector_mapping.json::blended_detector`
- **Confidence:** instruction-verified for positive finite envelopes

Within each adjacent group blend floored 20*log10(peak) with floored 10*log10(2*power), using the selected calibration weight. Interpolate the two group levels, subtract 3.0103 dB and the control-dependent offset, then subtract the lookup origin (-70). The zero-input branch requires separate path validation.

### First indexed peak/power blend

- **RVA:** `0x5d172e–0x5d17bf` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::mode2_peak_rms`
- **Confidence:** instruction-verified

Pdb=max(-90,20*log10(P)); Edb=max(-180,20*log10(2*E)); L=blend*Pdb+(1-blend)*max(-90,0.5*Edb) (nonpositive inputs use floors)

### Indexed 77-point gain curve interpolation

- **RVA:** `0x5d1833–0x5d18d6` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::mode2_lookup`
- **Confidence:** instruction-verified-structure

row stride 308 bytes; clamp endpoints; i=floor(u); y=C[i]+(u-i)*(C[i+1]-C[i]); runtime table values not recovered

### Reduction-dependent exponential attack increment

- **RVA:** `0x5d18d6–0x5d1946` (end exclusive)
- **Evidence:** `tvb_curve_provenance.json::mode2_nonlinear_attack`
- **Confidence:** instruction-verified local recurrence

For target C > prior G, delta=C-G; G_new=G+min(delta, A*(1-exp(-delta/B))*exp(-G/D)), with positive setup-dependent A,B,D.

### State- and target-dependent release

- **RVA:** `0x5d1946–0x5d1a52` (end exclusive)
- **Evidence:** `tvb_curve_provenance.json::mode2_adaptive_release`
- **Confidence:** instruction-verified structure

G_new=G+min(1, step/tau(G,C,H))*(C-G); tau=clamp(a*(max(0.05,G)/10)^(-p)*(1+k*H)/(1+max(C,0)/max(d,0.1)), lo, hi); selected constants a,p,k,d,lo,hi not mapped to UI.

### Secondary history state

- **RVA:** `0x5d1a52–0x5d1a90` (end exclusive)
- **Evidence:** `tvb_curve_provenance.json::mode2_history`
- **Confidence:** instruction-verified local recurrence

H_new=H+alpha*(0.05*G_new-H); primary reduction G_new stored in 0xd48 and 0x204; H stored in 0xd4c.

### Conventional compressor target gain reduction

- **RVA:** `0x5d1b2c–0x5d1bac` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::mode0_knee`
- **Confidence:** instruction-verified

u=L-T; s=1-1/R; K>0.001: 0 below -K/2; s*(u+K/2)^2/(2*K) inside knee; s*u above K/2. K<=0.001: max(0,u)*s

### Two independent gain-reduction states

- **RVA:** `0x5d1bac–0x5d1c1b` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::dual_recovery`
- **Confidence:** instruction-verified

g_j <- g_j + alpha_j*(G-g_j); alpha_j selected by G>g_j; output max(g_1,g_2)

### Single gain-reduction state

- **RVA:** `0x5d1c1b–0x5d1c52` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::single_recovery`
- **Confidence:** instruction-verified

g <- g + alpha*(G-g); attack alpha if G>g, release alpha otherwise

### dB to linear multiplier

- **RVA:** `0x5d1c9a–0x5d1cd9` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::gain_conversion`
- **Confidence:** instruction-verified

gain=10^(-g/20) if -g>-100 dB; else zero; then two additional gain factors

### Final output blend

- **RVA:** `0x5d1c9a–0x5d1f25` (end exclusive)
- **Evidence:** `tvb_extended_dsp.json::mix`
- **Confidence:** instruction-verified local algebra/structure; runtime unverified

Output = O_linear*((1-mix)*saved_dry + mix*colored_wet), or O_linear*wet when blend branch inactive. Makeup path includes further factors; exact mode-dependent calibration not asserted.

### Optical mode output coloration

- **RVA:** `0x5d1d79–0x5d1e88` (end exclusive)
- **Evidence:** `tvb_coloration.json::mode2_audio_color`
- **Confidence:** instruction-verified local recurrence

With x the post-gain sample, x+(a*x*x+b*x*abs(x))/(1+abs(x)/c) feeds two serial DF2T-shaped double-precision stages. Mode-specific data references verified.

### FET mode output coloration

- **RVA:** `0x5d1e8a–0x5d1ee1` (end exclusive)
- **Evidence:** `tvb_coloration.json::mode1_audio_color`
- **Confidence:** instruction-verified local recurrence

With x the post-gain sample, asymmetric polynomial max(floor,x+a*x*x+b*x*abs(x)) feeds three serial DF2T stages. Scalar constants fingerprinted, not exported.

### Output gain and optional parallel blend

- **RVA:** `0x5d1ee1–0x5d1f1e` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::output_blend`
- **Confidence:** instruction-verified

y=out_gain*((1-m)*dry+m*processed) when blend flag is set; otherwise out_gain*processed

### Time-to-coefficient helper

- **RVA:** `0x5d22e0–0x5d231c` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::time_helper`
- **Confidence:** instruction-verified

alpha=1-exp(-1/(0.001*t*F)); arguments t and F; no zero-time guard in helper

### Three post-gain filter sections

- **RVA:** `0x5d2330–0x5d241d` (end exclusive)
- **Evidence:** `tvb_coloration.json::fet_color_filter`
- **Confidence:** instruction-verified structure

Selected row contains 15 double coefficients in 120 bytes, three stages with 6 double state values per channel. Linear responses computed locally, no vendor coefficient arrays published.

### Rate-dependent optical output filter coefficients

- **RVA:** `0x5d29e6–0x5d2b46` (end exclusive)
- **Evidence:** `tvb_coloration.json::opto_color_filter_setup`
- **Confidence:** instruction-verified structure

First filter is first order (b2=a2=0); second is a biquad with b1=a1. Coefficient generation uses tan, pow, sin, cos with stored rate. Full runtime response not measured.

### Indexed 61-point gain curve interpolation

- **RVA:** `0x5d30b0–0x5d3121` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::mode1_lookup`
- **Confidence:** instruction-verified-structure

u = input - origin; clamp endpoints; i=floor(u); y=C[i]+(u-i)*(C[i+1]-C[i]); row stride 244 bytes; runtime table values not recovered

### Standalone soft-knee helper

- **RVA:** `0x5d3130–0x5d31a3` (end exclusive)
- **Evidence:** `tvb_dynamics_equations.json::knee_helper`
- **Confidence:** instruction-verified-structure

same quadratic knee motif as mode0_knee; exact caller relationships not established

### De-esser crossover and time coefficient setup

- **RVA:** `0x5d3c5e–0x5d3dfd` (end exclusive)
- **Evidence:** `tvb_extended_dsp.json::deess_setup`
- **Confidence:** instruction-verified local algebra/structure; runtime unverified

Crossover cutoff=clamp(field150*mode_scale,2000,12000) with scale 1.3,1,0.75. Detector retention exp(-1/(Fs*t)) with t=.00012 or .028 seconds; gain envelope retention uses fields 0x16c/0x170 in ms. Ratio slope=1-1/R.

### De-esser linked level, progressive gain law and output choices

- **RVA:** `0x5d3e44–0x5d401e` (end exclusive)
- **Evidence:** `tvb_extended_dsp.json::deess_gain`
- **Confidence:** instruction-verified local algebra/structure; runtime unverified

Linked p=max(abs(high[channel])). E=retain*Eold+(1-retain)*p; L=max(-120,20log10(E)); u=L-T. For u>0, target=min(cap,(1-1/R)*u*(1+0.55*clamp(u/8,0,1))), else 0. Separate attack/release GR smoothing, gain=10^(-GR/20) above -100dB. Mode field 0x160 selects wideband (1) versus split-band; flag0x164 excludes low component.

### Split-band output sample write

- **RVA:** `0x5d4112–0x5d4137` (end exclusive)
- **Evidence:** `tvb_extended_dsp.json::deess_split`
- **Confidence:** instruction-verified local algebra/structure; runtime unverified

Split output=high*gain+low, or high*gain with low excluded.

### Mid/side width with interpolated decorrelation and optional DC/high-pass recurrence

- **RVA:** `0x5d5f66–0x5d6034` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::width`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

S=width*((L-R)/2 + d*(tapA-tapB)/2), optional first-order high-pass/DC recurrence on S; L_out=M+S,R_out=M-S. Two interpolated history taps. Mid history write at 0x5d5d3f; exact knob mappings remain.

### Stereo fractional delay interpolation and feedback routing

- **RVA:** `0x5d6a55–0x5d6bac` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::delay`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

Linear fractional ring read d=(1-t)*buf[i]+t*buf[i+1] per channel; two first-order smoothing stages in feedback path and selectable cross-channel versus ordinary write routing. Full coefficient/control mapping unresolved.

### Decay-duration denominator and input sample-rate field

- **RVA:** `0x5d8000–0x5d8078` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::decay_setup`
- **Confidence:** exact-source local instruction evidence; runtime unverified

T=max(field_0x158,0.1). The UI-to-field mapping is not established by this check.

### Damping setup and complementary one-pole coefficients

- **RVA:** `0x5d80d6–0x5d82bc` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::damping_complements`
- **Confidence:** exact-source local instruction evidence; runtime unverified

a=exp(-2*pi*f_a/Fs), b=exp(-2*pi*f_b/Fs). Complement weights 1-a and 1-b. Input cutoff-control mappings remain incomplete.

### Four serial allpass-shaped diffusion cells

- **RVA:** `0x5d861e–0x5d8689` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::input_diffusion`
- **Confidence:** exact-source local instruction evidence; runtime unverified

Each of four 32-byte cells reads d, computes y=d-k*x, writes x+k*y, passes y to the next cell. Delay lengths and k range not established here.

### Eight-lane accumulation

- **RVA:** `0x5d8a61–0x5d8ec3` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::sum_all_lanes`
- **Confidence:** exact-source local instruction evidence; runtime unverified

Accumulate the eight per-lane values v_i and store them before feedback writes. xmm13 is zeroed in setup.

### Per-lane RT60-style decay factor and optional bounded coloration

- **RVA:** `0x5d8a90–0x5d8cb4` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::lane_decay`
- **Confidence:** exact-source local instruction evidence; runtime unverified

Base delay seconds d=lerp(two delay anchors,morph)*scale; base delay samples=d*Fs before modulation. Two one-pole states p=a*p_old+(1-a)*tap, q=b*q_old+(1-b)*p; feedback lane v=(p-q)*10^(-3*d/T). Optional nonlinear v=tanh(h*v)/tanh(h). Actual broadband decay depends on damping, modulation and nonlinear processing.

### Eight indexed modulated reverb lanes and bounded coloration

- **RVA:** `0x5d8ba7–0x5d8ec3` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::reverb`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

Modulated fractional delay taps, per-lane two-state damping, optional tanh normalization. Unrolled pair loop covers eight lane indices. Full feedback matrix and decay mapping not yet proven.

### Eight separate phase accumulators with wrap

- **RVA:** `0x5d8ec3–0x5d9074` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::modulation_phases`
- **Confidence:** exact-source local instruction evidence; runtime unverified

phi_i <- phi_i+f_i/Fs; if phi_i>=1 subtract 1. Per-lane sine modulation. No vendor calibration arrays exported.

### Householder feedback mixing with alternating input polarity

- **RVA:** `0x5d9074–0x5d9218` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::householder`
- **Confidence:** exact-source local instruction evidence; runtime unverified

For i=0..7, delay_write_i=v_i-(2/8)*sum(v)+(-1)^i*input/4. The linear matrix H=I-(2/8)11^T is orthogonal. Lane damping and input injection are separate; orthogonality alone does not prove whole-loop stability.

### Input-linked ducking envelope and wet gain

- **RVA:** `0x5d924c–0x5d938b` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::ducking`
- **Confidence:** exact-source local instruction evidence; runtime unverified

E=a*Eprev+(1-a)*max(abs(L),abs(R)), separate rise/fall coefficients. For positive E, d=max(-60,20*log10(E)); otherwise d=-60. u=clamp((d+35)/20,0,1). For positive duck amount q, reduction=-15*q*u dB, wet factor=10^(reduction/20) above -100 dB, otherwise zero. Nonpositive q gives unity. Host range of q remains unknown.

### Wet highpass-shaped tone and additive output

- **RVA:** `0x5d93ef–0x5d9548` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::wet_output`
- **Confidence:** exact-source local instruction evidence; runtime unverified

One-pole state per wet channel, then wet+(tone-1)*(wet-state); pass to normalized tanh helper. Output is dry plus shaped wet multiplied by smoothed wet gain and duck factor. Exact host control mapping remains unverified.

### Output color helper

- **RVA:** `0x5d9a70–0x5d9ae8` (end exclusive)
- **Evidence:** `tvb_reverb_feedback.json::wet_saturation`
- **Confidence:** exact-source local instruction evidence; runtime unverified

For color c>0.0001, h=1+4*c and y=tanh(h*x)/tanh(h); otherwise identity.

### Limiter three 12-tap fractional-phase peak candidates

- **RVA:** `0x5dd820–0x5ddb3f` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::limiter_interpolator`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

In enabled branch, three 12-coefficient dot products at 0x2a0/0x2d0/0x300 on channel history; maximum of absolute values and prior peak. Exact fractional-phase positions and true-peak compliance not established.

### Monotonic peak queue and soft-knee target

- **RVA:** `0x5ddbbe–0x5ddd17` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::limiter_peak`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

Timestamped monotonic peak queue expires entries older than lookahead interval. Excess u=peak_dB-ceiling_dB. For half-knee h>0 and -h<u<h, target GR=(u+h)^2/(4h); otherwise max(u,0).

### Delayed gain and final sample ceiling

- **RVA:** `0x5de006–0x5de079` (end exclusive)
- **Evidence:** `tvb_rack_paths.json::limiter_output`
- **Confidence:** exact-source instruction-verified local relationships; runtime unverified

y=clamp(delayed_audio*linear_gain,-ceiling_linear,ceiling_linear). Sample ceiling is not a certified intersample bound.


