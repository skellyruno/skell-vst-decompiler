"""Owned C++ fixture variant: disassembler agreement and no semantic overclaim."""
from pathlib import Path
import subprocess
import tempfile
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.navigation import runtime_ranges
from skell_vst_decompiler.structural_match import compare

SOURCE='''
extern "C" { int _fltused = 0; }
extern "C" __declspec(noinline) float inner(float x) { return x*x; }
extern "C" __declspec(dllexport) __declspec(noinline)
float wrapper(float x) { volatile float buf[16]; buf[0]=inner(x)*VARIANT; buf[1]=x; buf[2]=buf[0]*buf[1]; return buf[2]+buf[0]; }
'''

def main():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        binaries=[]
        for variant in (2,3):
            src=root/f'owned{variant}.cpp';obj=root/f'owned{variant}.obj';dll=root/f'owned{variant}.epl'
            src.write_text(SOURCE)
            subprocess.run(['clang++','--target=x86_64-pc-windows-msvc','-O2','-funwind-tables',
                '-ffreestanding','-fno-exceptions','-fno-rtti',f'-DVARIANT={variant}','-c',str(src),'-o',str(obj)],check=True,timeout=30)
            subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib',f'/out:{dll}',str(obj)],check=True,timeout=30)
            pe=PE(dll);regions=[(a,b) for a,b,_ in runtime_ranges(pe) if b-a>=32]
            assert regions,(dll,pe.inventory())
            binaries.append((dll,regions[0][0]))
        a,b=binaries
        result=compare(a[0],a[1],b[0],b[1])
        assert result['ordered_mnemonic_similarity']>=.9 and not result['exact_region_bytes_identical'],result
        assert result['decoder_consensus']
        print('Owned MSVC-target variant mnemonic comparison passed; no vendor execution.')

if __name__=='__main__':main()
