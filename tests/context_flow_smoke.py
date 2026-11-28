"""Compile owned PE fixtures; check actual GNU/LLVM static decodes, never load DLLs."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from skell_vst_decompiler.context_flow import compare_alias_context


def main():
    results=[]
    with tempfile.TemporaryDirectory(prefix='skell-context-') as temp:
        root=Path(temp)
        for bits,arch,machine in ((32,'i686','x86'),(64,'x86_64','x64')):
            for name,code,child_offset,child_size in (
                ('reentry','eb 04 eb 02 90 c3 eb fc',2,4),
                ('wait_alias','9b db e2 90 c3',3,2)):
                source=root/'owned.s';obj=root/'owned.obj';dll=root/'owned.dll'
                symbol='_probe' if bits==32 else 'probe'
                feature='.globl @feat.00\n.set @feat.00, 1\n' if bits==32 else ''
                source.write_text('.text\n'+feature+'.globl '+symbol+'\n'+symbol+':\n.byte '+','.join('0x'+b for b in code.split())+'\n')
                subprocess.run(['clang','--target='+arch+'-pc-windows-msvc','-c',str(source),'-o',str(obj)],check=True,timeout=30)
                subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/machine:'+machine,'/Brepro','/export:probe','/out:'+str(dll),str(obj)],check=True,timeout=30)
                data=dll.read_bytes();pe=struct.unpack_from('<I',data,60)[0];opt=pe+24
                n=struct.unpack_from('<H',data,pe+6)[0];optsz=struct.unpack_from('<H',data,pe+20)[0]
                base=struct.unpack_from('<I' if bits==32 else '<Q',data,opt+(28 if bits==32 else 24))[0]
                sections=[struct.unpack_from('<8sIIIIIIHHI',data,opt+optsz+40*i) for i in range(n)]
                text,=[s for s in sections if s[0].rstrip(b'\0')==b'.text']
                _,vs,rva,size,offset,*_=text;scope=bytes.fromhex(code);start=base+rva
                if data[offset:offset+len(scope)]!=scope or vs<len(scope):raise RuntimeError('Fixture bytes changed')
                def decode(addr,length):
                    args=['-d','-z',f'--start-address={addr:#x}',f'--stop-address={addr+length:#x}',str(dll)]
                    return (subprocess.check_output(['objdump','-w',*args],text=True,timeout=30),subprocess.check_output(['llvm-objdump',*args],text=True,timeout=30))
                g,l=decode(start,len(scope));cg,cl=decode(start+child_offset,child_size)
                r=compare_alias_context(scope,start,g,l,start+child_offset,child_size,cg,cl,bits=bits)
                normalized=r['normalized']
                if name=='reentry':
                    if normalized['local_reached_spans']!=1 or normalized['same_seed_enclosing']['additional_spans']!=2:raise RuntimeError(str(r))
                elif normalized['enclosing_entry_seed']['reached_comparable_spans']!=2:
                    raise RuntimeError(str(r))
                if dll.read_bytes()!=data:raise RuntimeError('Fixture modified')
                results.append({'bits':bits,'case':name,'binary_sha256':hashlib.sha256(data).hexdigest(),**r})
    print('SKELL_CONTEXT_FLOW_RESULT '+json.dumps(results,sort_keys=True))


if __name__=='__main__':main()
