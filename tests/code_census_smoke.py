"""Compile owned PE fixtures and compare actual GNU/LLVM decoding, never load them."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from skell_vst_decompiler.code_census import compare


def main():
    reports=[]
    with tempfile.TemporaryDirectory(prefix='skell-code-census-') as d:
        root=Path(d)
        src=root/'owned.c'
        src.write_text('__declspec(noinline) int inner(int x){return x*3+1;}\n__declspec(dllexport) int probe(int x){return inner(x)+2;}\n')
        for bits,arch,machine in [(32,'i686','x86'),(64,'x86_64','x64')]:
            for opt in ('-O0','-O2'):
                obj=root/'owned.obj';dll=root/'owned.dll'
                subprocess.run(['clang','--target='+arch+'-pc-windows-msvc',opt,'-c',str(src),'-o',str(obj)],check=True,timeout=30)
                subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/machine:'+machine,'/Brepro','/out:'+str(dll),str(obj)],check=True,timeout=30)
                data=dll.read_bytes();pe=struct.unpack_from('<I',data,60)[0]
                count=struct.unpack_from('<H',data,pe+6)[0];optsz=struct.unpack_from('<H',data,pe+20)[0];o=pe+24
                base=struct.unpack_from('<I' if bits==32 else '<Q',data,o+(28 if bits==32 else 24))[0]
                sections=[struct.unpack_from('<8sIIIIIIHHI',data,o+optsz+40*i) for i in range(count)]
                text,= [s for s in sections if s[0].rstrip(b'\0')==b'.text']
                _,vs,rva,size,offset,*_=text
                code=data[offset:offset+min(vs,size)];start=base+rva
                common=['-d','-z',f'--start-address={start:#x}',f'--stop-address={start+len(code):#x}',str(dll)]
                g=subprocess.check_output(['objdump','-w',*common],text=True,timeout=30)
                l=subprocess.check_output(['llvm-objdump',*common],text=True,timeout=30)
                r=compare(code,start,g,l)
                if r['exact_span_agreement']<5 or r['direct_rel32_calls']<1 or r['return_mnemonics']<1 or r['different_span_at_shared_location']:
                    raise RuntimeError('Owned instruction evidence mismatch: '+str(r))
                if dll.read_bytes()!=data:raise RuntimeError('Input changed')
                reports.append({'bits':bits,'opt':opt,'binary_sha256':hashlib.sha256(data).hexdigest(),**r})
    print('SKELL_CODE_CENSUS_RESULT '+json.dumps(reports,sort_keys=True))


if __name__=='__main__':main()
