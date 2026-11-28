"""Verify metadata coverage on owned PE builds, never execute DLLs."""
import json
from pathlib import Path
import subprocess
import tempfile
from skell_vst_decompiler.extent_coverage import inspect


def main():
    rows=[]
    with tempfile.TemporaryDirectory(prefix='skell-extents-') as tmp:
        p=Path(tmp);src=p/'owned.c';obj=p/'owned.obj';dll=p/'owned.dll'
        src.write_text('__declspec(noinline) int helper(int x){return x*3+1;}\n__declspec(dllexport) int probe(int x){volatile int a[32];a[0]=x;return helper(a[0])+2;}\n')
        for bits,arch,machine in [(32,'i686','x86'),(64,'x86_64','x64')]:
            for opt in ('-O0','-O2'):
                subprocess.run(['clang','--target='+arch+'-pc-windows-msvc',opt,'-c',str(src),'-o',str(obj)],check=True,timeout=30)
                subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/machine:'+machine,'/Brepro','/out:'+str(dll),str(obj)],check=True,timeout=30)
                data=dll.read_bytes();r=inspect(data)
                oracle=subprocess.check_output(['objdump','-f',str(dll)],text=True,timeout=30)
                assert ('i386:x86-64' if bits==64 else 'architecture: i386,') in oracle
                assert r['bits']==bits and r['executable_mapped_file_bytes']>0
                assert r['executable_raw_bytes']>=r['executable_mapped_file_bytes']
                if bits==64:
                    assert r['runtime_records']>0 and r['runtime_record_mapped_bytes']>0
                    assert r['runtime_record_union_bytes']==r['runtime_record_mapped_bytes']
                else:assert r['mapped_bytes_without_runtime_record'] is None
                assert dll.read_bytes()==data
                rows.append({'optimization':opt,**r})
    print('SKELL_EXTENT_COVERAGE_RESULT '+json.dumps(rows,sort_keys=True))


if __name__=='__main__':main()
