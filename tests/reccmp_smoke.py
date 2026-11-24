"""Exercise standalone reccmp export comparison on owned i386 DLLs only."""
import json
from pathlib import Path
import subprocess
import tempfile
from skell_vst_decompiler.legacy_pe import LegacyPE
from skell_vst_decompiler.pe_export_audit import export_metadata


def main():
    with tempfile.TemporaryDirectory(prefix='skell-reccmp-') as d:
        root=Path(d)
        def build(name,opt,extra):
            src=root/(name+'.c');obj=root/(name+'.obj');dll=root/(name+'.dll');pdb=root/(name+'.pdb')
            src.write_text('__declspec(dllexport) int probe(int x){return x*3+1;}\n'+
                           ('__declspec(dllexport) int additional(int x){return x+1;}\n' if extra else ''))
            subprocess.run(['clang','--target=i686-pc-windows-msvc',opt,'-gcodeview','-g','-c',str(src),'-o',str(obj)],check=True,timeout=30)
            subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/machine:x86','/debug','/Brepro','/out:'+str(dll),'/pdb:'+str(pdb),str(obj)],check=True,timeout=30)
            return dll,pdb
        original,_=build('original','-O0',False)
        same,pdb=build('same','-O2',False)
        different,pdb2=build('different','-O2',True)
        def run(target,symbols):
            result=subprocess.run(['reccmp-verexp','--paths',str(original),str(target),str(symbols),str(root),'--no-color'],capture_output=True,text=True,timeout=45)
            print(result.stdout);print(result.stderr)
            return result
        metadata=[export_metadata(x,('probe','additional')) for x in (original,same,different)]
        print('SKELL_RECCMP_LAYOUT '+json.dumps(metadata,sort_keys=True),flush=True)
        yes=run(same,pdb);no=run(different,pdb2)
        if yes.returncode!=0 or no.returncode!=1 or 'additional' not in no.stdout+no.stderr:
            raise RuntimeError('Reccmp export comparison failed; inspect recorded table layout and upstream parser. No success inferred.')
        inventories=[LegacyPE(x).inventory() for x in (original,same,different)]
        if [x['exports']['named_count'] for x in inventories]!=[1,1,2]:
            raise RuntimeError('Independent legacy export count disagrees')
        print('SKELL_RECCMP_RESULT '+json.dumps({'original_sha256':inventories[0]['binary_sha256'],
          'same_sha256':inventories[1]['binary_sha256'],'different_sha256':inventories[2]['binary_sha256'],
          'same_exports_pass':True,'changed_exports_detected':True,'owned_i386':True},sort_keys=True))


if __name__=='__main__':main()
