"""Offline, read-only PE/DSP evidence CLI. Does not execute plugin binaries."""
import argparse
import json
from pathlib import Path
from .disasm import disassemble, direct_calls, rip_data_refs
from .equations import trace_tvb_first_biquad, trace_tvb_biquad_bank
from .pe import PE


def main(argv=None):
    p=argparse.ArgumentParser(description="Skell VST Decompiler: read-only PE and DSP evidence")
    p.add_argument("binary",help="Locally owned Windows x64 VST3/EPL binary")
    p.add_argument("--mode",choices=["inventory","trace","tvb-biquad","tvb-bank"],default="inventory")
    p.add_argument("--rva",type=lambda x:int(x,0))
    p.add_argument("--bytes",dest="length",type=int,default=2048)
    p.add_argument("--objdump",default="objdump")
    p.add_argument("--out",type=Path,help="Write JSON findings; never writes to input binary")
    a=p.parse_args(argv)
    pe=PE(a.binary)
    if a.out and a.out.resolve()==Path(a.binary).resolve():
        p.error("Output cannot overwrite the original binary")
    if a.mode=="inventory":res=pe.inventory()
    elif a.mode=="tvb-biquad":res={"sha256":pe.sha256,"evidence":trace_tvb_first_biquad(pe,a.objdump)}
    elif a.mode=="tvb-bank":res=trace_tvb_biquad_bank(pe,a.objdump)
    else:
        if a.rva is None:p.error("--mode trace requires --rva")
        ins=disassemble(pe,a.rva,a.length,a.objdump)
        res={"sha256":pe.sha256,"rva":hex(a.rva),"requested_bytes":a.length,
            "instruction_count":len(ins),"direct_calls":direct_calls(pe,ins),
            "rip_data_references":rip_data_refs(pe,ins),
            "caveat":"Code pointers/constants are evidence only; no complete DSP signal path inferred."}
    payload=json.dumps(res,indent=2,allow_nan=False)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(payload+"\n",encoding="utf-8")
    print(payload)
    return 0


if __name__=="__main__":raise SystemExit(main())
