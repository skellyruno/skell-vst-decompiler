"""Evidence-gated math motifs (not claims of complete commercial DSP)."""
import re
from .disasm import disassemble

TVB_COMPRESSOR_FIRST_BIQUAD = {
    "first_rva":0x5D07BF,
    "coeffs":[0x520,0x524,0x528,0x52c,0x530],
    "states":[0x718,0x71c],
    "required":[
        (0x5d07c6,"mulss","xmm2,DWORD PTR [rsi+0x520]"),
        (0x5d07d5,"mulss","xmm1,DWORD PTR [rsi+0x524]"),
        (0x5d07dd,"addss","xmm2,DWORD PTR [rax+rsi*1+0x718]"),
        (0x5d07ec,"mulss","xmm0,DWORD PTR [rsi+0x52c]"),
        (0x5d07f4,"subss","xmm1,xmm0"),
        (0x5d07fb,"addss","xmm1,DWORD PTR [rax+rsi*1+0x71c]"),
        (0x5d0804,"movss","DWORD PTR [rax+rsi*1+0x718],xmm1"),
        (0x5d0810,"mulss","xmm1,DWORD PTR [rsi+0x528]"),
        (0x5d0818,"mulss","xmm0,DWORD PTR [rsi+0x530]"),
        (0x5d0820,"subss","xmm1,xmm0"),
        (0x5d0824,"movss","DWORD PTR [rax+rsi*1+0x71c],xmm1"),
    ],
}

# Original user-supplied TVB Rack V2.vst3, fingerprinted in earlier research.
TVB_SHA256 = "cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9"


def verify_tvb_first_biquad(ins, image_base, source_sha256):
    """Conservative exact-build proof: all eleven instructions must match in order."""
    if source_sha256 != TVB_SHA256:
        raise ValueError("Different TVB build: previously verified offsets cannot be reused")
    indexed={i.address-image_base:i for i in ins}
    for rva, mnemonic, operands in TVB_COMPRESSOR_FIRST_BIQUAD["required"]:
        i=indexed.get(rva)
        if i is None or i.mnemonic != mnemonic or i.operands != operands:
            raise ValueError(f"BiQuad opcode/dataflow evidence missing at RVA {rva:#x}")
    return {
        "status":"instruction-verified-for-one-stage",
        "function":"TVB compressor candidate native per-block method",
        "first_stage_rva":hex(TVB_COMPRESSOR_FIRST_BIQUAD["first_rva"]),
        "coefficient_offsets":[hex(x) for x in TVB_COMPRESSOR_FIRST_BIQUAD["coeffs"]],
        "channel_state_offsets":[hex(x) for x in TVB_COMPRESSOR_FIRST_BIQUAD["states"]],
        "math":["y=b0*x+z1", "z1'=b1*x-a1*y+z2", "z2'=b2*x-a2*y"],
        "caveat":"This does not establish audio-versus-sidechain role or parameter mapping; other processing modes branch around this stage."
    }


def trace_tvb_first_biquad(pe, objdump="objdump"):
    instructions=disassemble(pe,0x5d07bf,0x80,objdump=objdump)
    return verify_tvb_first_biquad(instructions,pe.image_base,pe.sha256)


class IndependentDF2T:
    """Clean-room mathematical test utility, NOT copied production/vendor code."""
    def __init__(self,b0,b1,b2,a1,a2):
        self.b0,self.b1,self.b2,self.a1,self.a2=(float(x) for x in (b0,b1,b2,a1,a2))
        self.z1=self.z2=0.0

    def process(self,x):
        y=self.b0*x+self.z1
        z1=self.b1*x-self.a1*y+self.z2
        z2=self.b2*x-self.a2*y
        self.z1,self.z2=z1,z2
        return y


def trace_tvb_biquad_bank(pe, objdump="objdump"):
    """Prove 24 repeated DF2T-shaped stages, without claiming their system role.

    The native mode-2 branch starts at 0x5D07BF; its per-channel state stride
    is computed by `lea rax,[rbx+rbx*2]` then `shl rax,0x6` (3*64=192).
    Confirm both instructions, all five coefficient references and two state
    writes for *each* of 24 sections. No claims about measured sound/routing.
    """
    if pe.sha256 != TVB_SHA256:
        raise ValueError("Fingerprint mismatch: need new code analysis for this build")
    ins=disassemble(pe,0x5D07BF,0x9C0,objdump=objdump)
    first=verify_tvb_first_biquad(ins,pe.image_base,pe.sha256)
    code=[i.text for i in ins]
    if "lea rax,[rbx+rbx*2]" not in code or "shl rax,0x6" not in code:
        raise ValueError("Channel state stride instructions missing")
    stages=[]
    for stage in range(24):
        start=0x520+stage*0x14
        states=(0x718+stage*8,0x71c+stage*8)
        for offset in range(start,start+20,4):
            # All coefficients of each stage are multiplied into a scalar
            # floating-point calculation (not inferred from a filename/UI).
            pattern=f"[rsi+{hex(offset)}]"
            if not any(i.mnemonic=="mulss" and pattern in i.operands for i in ins):
                raise ValueError(f"Missing coefficient operand at {offset:#x}")
        for offset in states:
            pattern=f"[rax+rsi*1+{hex(offset)}]"
            if not any(i.mnemonic=="movss" and i.operands.startswith("DWORD PTR "+pattern+",") for i in ins):
                raise ValueError(f"Missing persistent state update {offset:#x}")
        stages.append({"number":stage+1,"coeff_offsets":[hex(x) for x in range(start,start+20,4)],
                       "state_offsets":[hex(x) for x in states]})
    if stages[-1]['state_offsets'] != ['0x7d0','0x7d4']:
        raise ValueError("Unexpected terminal state offsets")
    return {
        "build_sha256":pe.sha256,
        "evidence_status":"24 repeated 5-coefficient/two-state filter update motifs verified",
        "first_stage":first,
        "branch_entry_rva":"0x5d07bf",
        "branch_selector":"r12d == 2, identified from `cmp`/`jne` at 0x5d07b5",
        "channel_state_stride_bytes":192,
        "stage_count":len(stages),"stages":stages,
        "not_proven":"Filter cutoff/Q assignment, audio/detector signal routing, gain law, sound equivalence, 24 UI bands linkage"
    }
