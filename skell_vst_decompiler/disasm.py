"""Bounded objdump x64 disassembly with exact address and instruction parsing.

Uses objdump as a *reader*, never runs the target binary. Text is evidence,
not decompiled source code; malformed/truncated output is rejected.
"""
from dataclasses import dataclass
import math
import re
import struct
import shutil
import subprocess
from .pe import PEFormatError

LINE = re.compile(r"^\s*([0-9a-fA-F]+):\s*([a-z][a-z0-9.]*)\s*(.*?)\s*$")
HEX = re.compile(r"^\s*([0-9a-fA-F]+):\s*([0-9a-fA-F ]+?)\s{2,}([a-z][a-z0-9.]*)\s*(.*?)\s*$")
TARGET = re.compile(r"(?:#\s*)?0x([0-9a-fA-F]+)")


@dataclass(frozen=True)
class Instruction:
    address: int
    mnemonic: str
    operands: str

    @property
    def text(self): return f"{self.mnemonic} {self.operands}".strip()


def parse_disassembly(stdout):
    parsed=[]
    for line in stdout.splitlines():
        match=LINE.match(line)
        if match is None:
            match=HEX.match(line)
            if match is None:continue
            addr,_,op,args=match.groups()
        else:addr,op,args=match.groups()
        parsed.append(Instruction(int(addr,16),op,args.strip()))
    return parsed


def disassemble(pe, start_rva, length, objdump="objdump"):
    if not isinstance(start_rva,int) or not isinstance(length,int) or length<1 or length>32768:
        raise ValueError("Bounded disassembly requires 1..32768 bytes")
    pe.at_rva(start_rva,length,executable=True)
    if not shutil.which(objdump):
        raise RuntimeError("Install binutils objdump or choose --objdump explicitly")
    start=pe.image_base+start_rva
    argv=[objdump,"-d","-M","intel","--no-show-raw-insn",f"--start-address={hex(start)}",f"--stop-address={hex(start+length)}",str(pe.path)]
    response=subprocess.run(argv,capture_output=True,text=True,timeout=25,check=False)
    if response.returncode or len(response.stdout)>6_000_000:
        raise RuntimeError("objdump failed or exceeded the output bound: "+response.stderr[:300])
    ins=parse_disassembly(response.stdout)
    if not ins or not (start<=ins[0].address<start+length):
        raise PEFormatError("No disassembly at requested executable RVA")
    return ins


def direct_calls(pe, ins):
    results=[]
    for i in ins:
        if i.mnemonic!="call":continue
        m=re.fullmatch(r"0x([0-9a-f]+)",i.operands)
        if not m:continue
        va=int(m.group(1),16)
        rva=va-pe.image_base
        results.append({"site_rva":hex(i.address-pe.image_base),"target_rva":hex(rva)})
    return results


def imported_call_sites(pe, ins):
    """Resolve direct CALL -> jmp [RIP+disp32] import thunks, not indirect DSP."""
    symbols=pe.imports()
    import struct
    found=[]
    for item in direct_calls(pe, ins):
        target=int(item["target_rva"],16)
        try: code=pe.at_rva(target,6,executable=True)
        except PEFormatError:continue
        if code[:2] != b"\xff\x25":continue
        iat=target+6+struct.unpack_from("<i",code,2)[0]
        symbol=symbols.get(iat)
        if symbol:
            found.append({**item,"iat_rva":hex(iat),**symbol})
    return found


def rip_data_refs(pe, ins):
    refs=[]
    for i in ins:
        if "[rip+" not in i.operands and "[rip-" not in i.operands:continue
        match=re.search(r"#\s*0x([0-9a-fA-F]+)",i.operands)
        if not match:continue
        va=int(match.group(1),16)
        rva=va-pe.image_base
        if rva<0:continue
        try:
            raw = pe.at_rva(rva,4)
        except PEFormatError:continue
        # A pointer, code reference, or UTF-8 string is not automatically a DSP constant.
        # Only instructions with scalar floating-point memory operands qualify as
        # *candidate* float32 reads; exclude NaNs/infinities from machine-readable JSON.
        if i.mnemonic not in ("movss","mulss","addss","subss","divss","comiss","ucomiss","minss","maxss"):
            continue
        value=struct.unpack("<f",raw)[0]
        refs.append({"site_rva":hex(i.address-pe.image_base),"data_rva":hex(rva),
                     "raw_u32_le":hex(int.from_bytes(raw,'little')),
                     "float32_candidate":value if math.isfinite(value) else None,
                     "note":"Memory value only; not proven algorithm coefficient"})
    return refs
