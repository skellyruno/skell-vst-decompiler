"""Run standalone REA import inspection on freshly compiled owned DLLs."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
import pefile
from skell_vst_decompiler.rea_metadata import normalize


def main():
    cases=[]
    with tempfile.TemporaryDirectory(prefix='skell-rea-') as temp:
        root=Path(temp)
        for bits,arch,machine in [(32,'i686','x86'),(64,'x86_64','x64')]:
            def build(name,source,libs=()):
                c=root/(name+'.c');o=root/(name+'.obj');dll=root/(name+'.dll')
                c.write_text(source)
                subprocess.run(['clang','--target='+arch+'-pc-windows-msvc','-O2','-c',str(c),'-o',str(o)],check=True,timeout=30)
                subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/machine:'+machine,'/Brepro','/out:'+str(dll),'/implib:'+str(root/(name+'.lib')),str(o),*map(str,libs)],check=True,timeout=30)
                return dll
            provider=build('owned'+str(bits),'__declspec(dllexport) int probe(int x){return x*3+1;}')
            consumer=build('consumer'+str(bits),'__declspec(dllimport) int probe(int); __declspec(dllexport) int call(int x){return probe(x)+1;}',[provider.with_suffix('.lib')])
            for path,expected_count in [(provider,0),(consumer,1)]:
                data=path.read_bytes();sha=hashlib.sha256(data).hexdigest()
                p=subprocess.run(['rea','inspect-pe-imports',str(path),'--json'],capture_output=True,timeout=90)
                if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')+p.stdout[:2000].decode(errors='replace'))
                obs=normalize(p.stdout,sha,len(data))
                pe=pefile.PE(str(path))
                try:
                    rows=[]
                    for kind,attr in [('imports','DIRECTORY_ENTRY_IMPORT'),('delay_imports','DIRECTORY_ENTRY_DELAY_IMPORT')]:
                        for d in getattr(pe,attr,[]):
                            for f in d.imports:
                                rows.append((kind,d.dll.decode('ascii').lower(),f.name.decode('ascii') if f.name else None,f.ordinal if f.name is None else None,f.address-pe.OPTIONAL_HEADER.ImageBase))
                    if obs['rows']!=sorted(rows,key=repr) or obs['bits']!=bits or len(rows)!=expected_count:
                        raise RuntimeError('REA/pefile metadata disagreement')
                    if expected_count and obs['imphash']!=pe.get_imphash():raise RuntimeError('Import hash mismatch')
                finally:pe.close()
                if path.read_bytes()!=data:raise RuntimeError('Input modified')
                obs.pop('rows')
                cases.append({'bits':bits,'count':expected_count,'observation':obs,'agreed':True})
    print('SKELL_REA_RESULT '+json.dumps({'cases':cases,'all_agreed':True},sort_keys=True))

if __name__=='__main__':main()
