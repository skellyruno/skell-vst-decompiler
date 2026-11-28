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
from .navigation import function_report, reference_report
from .curve_provenance import verify_curves
from .detector_mapping import verify_detector_mapping
from .fieldrefs import field_report
from .coloration import verify_coloration
from .parameter_mapping import verify_parameter_mapping
from .extended_dsp import verify_extended, verify_vmr_utilities
from .rack_paths import verify_tvb_rack, verify_vmr_paths
from .reverb_feedback import verify_reverb


def main(argv=None):
    p=argparse.ArgumentParser(description="Skell VST Decompiler: read-only PE and DSP evidence")
    p.add_argument("binary",help="Locally owned Windows x64 VST3/EPL binary")
    p.add_argument("--mode",choices=["inventory","trace","tvb-biquad","tvb-bank","tvb-compressor-setup","tvb-dynamics","dispatch","tvb-curves","tvb-detector","tvb-color","tvb-parameters","tvb-extended","vmr-utilities","tvb-rack-paths","tvb-reverb","vmr-effect-paths","fieldrefs","function","xref"],default="inventory")
    p.add_argument("--find",help="Filter tvb-dynamics by keywords or hexadecimal RVA")
    p.add_argument("--entries",type=int,default=4,help="Candidate jump-table slots to inspect (1..32, not inferred table length)")
    p.add_argument("--target",type=lambda x:int(x,0),help="Target RVA for xref search")
    p.add_argument("--target-bytes",type=int,default=1)
    p.add_argument("--base",help="Base register for literal field search")
    p.add_argument("--offset",type=lambda x:int(x,0),help="Signed field displacement (use --offset=-0x50 for negative values)")
    p.add_argument("--rva",type=lambda x:int(x,0))
    p.add_argument("--bytes",dest="length",type=lambda x:int(x,0),default=2048)
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
    elif a.mode=="tvb-detector":
        res=verify_detector_mapping(pe,a.objdump)
        if a.find is not None:res=search(res,a.find)
    elif a.mode=="tvb-color":
        res=verify_coloration(pe,a.objdump)
        if a.find is not None:res=search(res,a.find)
    elif a.mode=="tvb-parameters":
        res=verify_parameter_mapping(pe,a.objdump)
        if a.find is not None:res=search(res,a.find)
    elif a.mode=="tvb-extended":
        res=verify_extended(pe,a.objdump)
        if a.find is not None:res=search(res,a.find)
    elif a.mode=="vmr-utilities":
        res=verify_vmr_utilities(pe,a.objdump)
    elif a.mode=="tvb-rack-paths":
        res=verify_tvb_rack(pe,a.objdump)
        if a.find is not None:res=search(res,a.find)
    elif a.mode=="tvb-reverb":
        res=verify_reverb(pe,a.objdump)
        if a.find is not None:res=search(res,a.find)
    elif a.mode=="vmr-effect-paths":
        res=verify_vmr_paths(pe,a.objdump)
        if a.find is not None:res=search(res,a.find)
    elif a.mode=="fieldrefs":
        if a.rva is None or a.base is None or a.offset is None:p.error("--mode fieldrefs requires --rva, --base and --offset")
        res=field_report(pe,a.rva,a.length,a.base,a.offset,a.objdump)
    elif a.mode=="tvb-curves":
        res=verify_curves(pe,a.objdump)
        if a.find is not None:res=search(res,a.find)
    elif a.mode=="function":
        if a.rva is None:p.error("--mode function requires --rva")
        res=function_report(pe,a.rva,a.objdump)
    elif a.mode=="xref":
        if a.rva is None or a.target is None:p.error("--mode xref requires --rva and --target")
        res=reference_report(pe,a.rva,a.length,a.target,a.target_bytes,a.objdump)
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
