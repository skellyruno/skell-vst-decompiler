"""Optional real Rizin smoke on our own compiled PE; never run the PE."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from ghidra_smoke import fixture_exports
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.classgraph import compare_rizin


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rizin',required=True)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); obj=root/'fixture.obj'; exe=root/'fixture.exe'
        source=Path(__file__).parent/'fixtures'/'ghidra_fixture.c'
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-fno-stack-protector','-c',str(source),'-o',str(obj)],check=True,timeout=30)
        subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/out:'+str(exe),str(obj)],check=True,timeout=30)
        pe=PE(exe); exports=fixture_exports(exe)
        run=subprocess.run([args.rizin,'-q','-e','scr.color=0','-c','aaa;aflj',str(exe)],capture_output=True,text=True,timeout=90,check=True)
        funcs=json.loads(run.stdout)
        result=compare_rizin(pe,{'binary_sha256':pe.sha256,'image_base':pe.image_base,'functions':funcs})
        valid={int(f['rva'],16) for f in result['functions'] if f['status']!='not_file_backed_executable'}
        if not set(exports.values())<=valid:
            raise RuntimeError('Rizin did not recover both fixture export entries')
        print(json.dumps({'fixture_sha256':pe.sha256,'exports':exports,'counts':result['counts']},indent=2))

if __name__=='__main__':main()
