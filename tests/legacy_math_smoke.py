"""Compile and inspect an owned x86 DLL and its consumer; never load them."""
import json
from pathlib import Path
import subprocess
import tempfile
from skell_vst_decompiler.legacy_pe import LegacyPE
from skell_vst_decompiler.legacy_math_audit import imports,relocations,summarize_scope


def main():
    with tempfile.TemporaryDirectory(prefix='skell-math-') as d:
        root=Path(d)
        for name,source in [('provider','__declspec(dllexport) int probe_math(int x){return x+1;}'),('consumer','__declspec(dllimport) int probe_math(int); __declspec(dllexport) int invoke(int x){return probe_math(x)+2;}')]:
            c=root/(name+'.c');o=root/(name+'.obj');dll=root/(name+'.dll');c.write_text(source)
            subprocess.run(['clang','--target=i686-pc-windows-msvc','-O2','-c',str(c),'-o',str(o)],check=True,timeout=30)
            args=['lld-link','/dll','/noentry','/nodefaultlib','/machine:x86','/Brepro','/out:'+str(dll),'/implib:'+str(root/(name+'.lib')),str(o)]
            if name=='consumer':args.append(str(root/'provider.lib'))
            subprocess.run(args,check=True,timeout=30)
        p=LegacyPE(root/'consumer.dll');slots,n=imports(p);sites,pad=relocations(p)
        if n!=1 or len(slots)!=1 or not sites:raise RuntimeError('Unexpected owned fixture metadata')
        observations=[]
        for s in p.sections:
            if not s['executable']:continue
            data=p.read(s['rva'],min(s['size'],s['virtual_size']));start=p.base+s['rva']
            args=['-d','-z',f'--start-address={start:#x}',f'--stop-address={start+len(data):#x}',str(p.path)]
            g=subprocess.check_output(['objdump','-w',*args],text=True,timeout=30)
            l=subprocess.check_output(['llvm-objdump',*args],text=True,timeout=30)
            observations.append(summarize_scope(data,start,p.base,g,l,slots,sites,allowed={'probe_math'}))
        if sum(x['public_math_call_counts'].get('probe_math',0) for x in observations)!=1:raise RuntimeError(str(observations))
        if p.path.read_bytes()!=p.data:raise RuntimeError('Fixture modified')
        print('SKELL_LEGACY_MATH_RESULT '+json.dumps({'binary_sha256':p.sha256,'descriptors':n,'slots':len(slots),'highlow_relocations':len(sites),'scopes':observations},sort_keys=True))


if __name__=='__main__':main()
