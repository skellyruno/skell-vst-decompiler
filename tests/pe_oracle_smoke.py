"""Real compiler fixtures, independent pefile metadata oracle, no DLL loading."""
import json
import subprocess
import tempfile
from pathlib import Path
import pefile
from skell_vst_decompiler.pe_export_audit import export_metadata


def main():
    cases=[]
    with tempfile.TemporaryDirectory(prefix='skell-pe-oracle-') as d:
        root=Path(d)
        for arch,target,machine in [('x86','i686-pc-windows-msvc','x86'),('x64','x86_64-pc-windows-msvc','x64')]:
            for opt in ('O0','O2'):
                for extra in (False,True):
                    src=root/'fixture.c';obj=root/'fixture.obj';dll=root/'fixture.dll'
                    src.write_text('__declspec(dllexport) int probe(int x){return 3*x+1;}\n'+
                       ('__declspec(dllexport) int additional(int x){return x+1;}\n' if extra else ''))
                    subprocess.run(['clang','--target='+target,'-'+opt,'-c',str(src),'-o',str(obj)],check=True,timeout=30)
                    subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/machine:'+machine,'/Brepro','/out:'+str(dll),str(obj)],check=True,timeout=30)
                    ours=export_metadata(dll,('probe','additional'))
                    ext=pefile.PE(str(dll),fast_load=True)
                    try:
                        ext.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
                        exports=ext.DIRECTORY_ENTRY_EXPORT
                        expected=[{'name':x.name.decode('ascii'),'rva':hex(x.address),'ordinal':x.ordinal,'forwarded':x.forwarder is not None}
                                  for x in exports.symbols if x.name is not None]
                        expected.sort(key=lambda x:x['name'])
                        assert ours['public_entries']==expected
                        assert ours['named_count']==exports.struct.NumberOfNames==(2 if extra else 1)
                        assert ours['address_count']==exports.struct.NumberOfFunctions
                        assert ours['architecture']==arch
                        assert int(ours['image_base'],16)==ext.OPTIONAL_HEADER.ImageBase
                        cases.append({'architecture':arch,'optimization':opt,'extra_export':extra,
                                      'sha256':ours['binary_sha256'],'export_count':ours['named_count'],
                                      'reccmp_contiguous_table_assumption':ours['reccmp_contiguous_table_assumption']})
                    finally:
                        ext.close()
    print('SKELL_PE_ORACLE_RESULT '+json.dumps({'pefile_version':pefile.__version__,'cases':cases,'all_agreed':True},sort_keys=True))


if __name__=='__main__':main()
