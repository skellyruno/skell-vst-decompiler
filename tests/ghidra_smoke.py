"""Real headless smoke test on our own compiled PE only; no third-party plugins."""
import argparse
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.ghidra_bridge import make_plan, run_analysis


def fixture_exports(path):
    pe=PE(path)
    optional=pe._unpack('<I',0x3c)[0]+24
    rva,size=pe._unpack('<II',optional+112)
    if not rva or size<40:raise RuntimeError('Fixture export directory missing')
    _,_,_,_,_,_,nf,nn,functions,names,ordinals=struct.unpack('<IIHHIIIIIII',pe.at_rva(rva,40))
    if not 1<=nn<=nf<=128:raise RuntimeError('Unexpected fixture export count')
    result={}
    for i in range(nn):
        name=pe.cstring_rva(pe.u32(names+4*i))
        ordinal,=struct.unpack('<H',pe.at_rva(ordinals+2*i,2))
        if ordinal>=nf:raise RuntimeError('Invalid export ordinal')
        target=pe.u32(functions+4*ordinal)
        if rva<=target<rva+size:raise RuntimeError('Unexpected forwarded export')
        pe.at_rva(target,1,executable=True)
        if name in ('smooth','apply_gain'):result[name]=target
    if set(result)!={'smooth','apply_gain'}:raise RuntimeError('Fixture exports not found')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ghidra-home',required=True);a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='skell-smoke-') as t:
        root=Path(t);obj=root/'fixture.obj';exe=root/'fixture.exe'
        source=Path(__file__).resolve().parent/'fixtures'/'ghidra_fixture.c'
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-fno-stack-protector','-c',str(source),'-o',str(obj)],check=True,timeout=30)
        subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/out:'+str(exe),str(obj)],check=True,timeout=30)
        targets=fixture_exports(exe);pe=PE(exe);plan=make_plan(pe,targets.values())
        try:
            result=run_analysis(pe,plan,a.ghidra_home,root/'jobs',120)
        except Exception:
            for log in root.glob('jobs/*/analyzer.log'):
                print(log.read_text(encoding='utf-8',errors='replace')[-18000:])
            raise
        if result['status']!='complete' or result['unique_decompiled_function_count']!=2:
            raise RuntimeError('Actual Ghidra did not decompile both fixture exports: '+json.dumps(result))
        if not any(int(e['entry_rva'],16)==targets['apply_gain'] and e['kind']=='calls' and int(e['related_rva'],16)==targets['smooth'] for e in result['call_links']):
            raise RuntimeError('Expected direct call relationship missing')
        print('REAL_GHIDRA_SMOKE_PASS '+json.dumps({'targets':targets,'functions':result['unique_decompiled_function_count'],'links':len(result['call_links'])}))

if __name__=='__main__':main()
