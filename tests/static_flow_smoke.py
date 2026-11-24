"""Verify bounded flow on owned PE fixtures, never load target DLLs."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from skell_vst_decompiler.static_flow import summarize


def main():
    results=[]
    with tempfile.TemporaryDirectory(prefix='skell-flow-') as d:
        root=Path(d)
        src=root/'owned.c'
        src.write_text('volatile int sink;\n__declspec(noinline) int inner(int x){return x*3+1;}\n__declspec(dllexport) int probe(int x){if(x>0){sink=x;return inner(x)+2;}sink=-x;return x-2;}\n')
        for bits,arch,machine in [(32,'i686','x86'),(64,'x86_64','x64')]:
            for opt in ('-O0','-O2'):
                obj=root/'owned.obj';dll=root/'owned.dll'
                subprocess.run(['clang','--target='+arch+'-pc-windows-msvc',opt,'-c',str(src),'-o',str(obj)],check=True,timeout=30)
                subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/machine:'+machine,'/Brepro','/out:'+str(dll),str(obj)],check=True,timeout=30)
                data=dll.read_bytes();pe=struct.unpack_from('<I',data,60)[0]
                count=struct.unpack_from('<H',data,pe+6)[0];optsz=struct.unpack_from('<H',data,pe+20)[0];o=pe+24
                base=struct.unpack_from('<I' if bits==32 else '<Q',data,o+(28 if bits==32 else 24))[0]
                sections=[struct.unpack_from('<8sIIIIIIHHI',data,o+optsz+40*i) for i in range(count)]
                def read(rva,n):
                    valid=[s for s in sections if s[2]<=rva and rva-s[2]+n<=s[3]]
                    if len(valid)!=1:raise ValueError('Invalid fixture RVA')
                    s=valid[0];offset=s[4]+rva-s[2];return data[offset:offset+n]
                exp,=struct.unpack_from('<I',data,o+(96 if bits==32 else 112))
                fields=struct.unpack('<IIHHIIIIIII',read(exp,40));nf,nn,ft,nt,ot=fields[6:]
                if nf!=1 or nn!=1:raise ValueError('Unexpected fixture exports')
                entry,=struct.unpack('<I',read(ft,4))
                text,=[s for s in sections if s[0].rstrip(b'\0')==b'.text']
                _,vs,rva,size,offset,*_=text
                code=data[offset:offset+min(vs,size)];start=base+rva
                common=['-d','-z',f'--start-address={start:#x}',f'--stop-address={start+len(code):#x}',str(dll)]
                g=subprocess.check_output(['objdump','-w',*common],text=True,timeout=30)
                l=subprocess.check_output(['llvm-objdump',*common],text=True,timeout=30)
                r=summarize(code,start,g,l,[base+entry],bits=bits);k=r['instruction_categories']
                if not (k.get('return',0)>=1 and k.get('conditional',0)>=1 and k.get('direct_call',0)==1 and r['not_reached_in_model']>0 and r['direct_call_destinations_not_followed'].get('agreed_start')==1 and not r['flow_destinations'].get('unverified_boundary') and not r['flow_destinations'].get('interior_of_span')):
                    raise RuntimeError('Owned flow observation mismatch: '+str(r))
                if dll.read_bytes()!=data:raise RuntimeError('Fixture modified')
                results.append({'bits':bits,'opt':opt,'binary_sha256':hashlib.sha256(data).hexdigest(),**r})
    print('SKELL_STATIC_FLOW_RESULT '+json.dumps(results,sort_keys=True))

if __name__=='__main__':main()
