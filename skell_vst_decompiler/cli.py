"""Offline, read-only PE/DSP evidence CLI. Does not execute plugin binaries."""
import argparse
import json
from collections import Counter
from pathlib import Path
from .disasm import disassemble, direct_calls, imported_call_sites, rip_data_refs
from .equations import TVB_SHA256, trace_tvb_first_biquad, trace_tvb_biquad_bank
from .pe import PE
from .dynamics import verify_dynamics
from .catalog import search
from .dispatch import trace_dispatch


def main(argv=None):
    p=argparse.ArgumentParser(description="Skell VST Decompiler: read-only PE and DSP evidence")
    p.add_argument("binary",help="Locally owned Windows x64 VST3/EPL binary")
    p.add_argument("--mode",choices=["inventory","trace","tvb-biquad","tvb-bank","tvb-compressor-setup","tvb-dynamics","dispatch"],default="inventory")
    p.add_argument("--find",help="Filter tvb-dynamics by keywords or hexadecimal RVA")
    p.add_argument("--entries",type=int,default=4,help="Candidate jump-table slots to inspect (1..32, not inferred table length)")
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
    elif a.mode=="dispatch":
        if a.rva is None:p.error("--mode dispatch requires --rva")
        res=trace_dispatch(pe,a.rva,a.entries,a.objdump)
    elif a.mode=="tvb-dynamics":
        res=verify_dynamics(pe,a.objdump)
        if a.find is not None:res=search(res,a.find)
    elif a.mode=="tvb-compressor-setup":
        if pe.sha256!=TVB_SHA256:
            raise ValueError("Exact source SHA-256 differs; refusing build-specific DSP claims")
        ins=disassemble(pe,0x5cfa7f,0xd40,a.objdump)
        imported=imported_call_sites(pe,ins)
        counts=dict(Counter(i["symbol"] for i in imported))
        expected={"expf":16,"powf":10,"logf":5}
        if any(counts.get(k)!=v for k,v in expected.items()):
            raise ValueError(f"Known compiler math-call path differs: {counts}")
        res={"sha256":pe.sha256,"region_rva":"0x5cfa7f-0x5d07bf",
             "math_call_counts":counts,"verified_import_call_count":len(imported),
             "calls":imported,"status":"instruction/import-thunk verified, mapping of controls to coefficients unknown"}
    else:
        if a.rva is None:p.error("--mode trace requires --rva")
        ins=disassemble(pe,a.rva,a.length,a.objdump)
        res={"sha256":pe.sha256,"rva":hex(a.rva),"requested_bytes":a.length,
            "instruction_count":len(ins),"direct_calls":direct_calls(pe,ins),
            "import_calls":imported_call_sites(pe,ins),
            "rip_data_references":rip_data_refs(pe,ins),
            "caveat":"Code pointers/constants are evidence only; no complete DSP signal path inferred."}
    payload=json.dumps(res,indent=2,allow_nan=False)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(payload+"\n",encoding="utf-8")
    print(payload)
    return 0


if __name__=="__main__":raise SystemExit(main())
