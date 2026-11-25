"""Compile owned PE functions with shared and distinct code, then index exact bytes."""
from pathlib import Path
import subprocess
import tempfile
from skell_vst_decompiler.shared_code import scan_modules, annotate

SOURCE = '''
extern "C" { int _fltused = 0; }
extern "C" __declspec(noinline) float inner(float x) { return x*x; }
extern "C" __declspec(dllexport) __declspec(noinline)
float shared_helper(float x) { volatile float buf[16]; buf[0]=inner(x)+0.125f; return buf[0]; }
extern "C" __declspec(dllexport) __declspec(noinline)
float unique_helper(float x) { volatile float buf[16]; buf[0]=inner(x)+x*VARIANT+1.0f; return buf[0]; }
'''


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        for i in range(3):
            src=root/f'engine{i}.cpp';obj=root/f'engine{i}.obj';dll=root/f'engine{i}.epl'
            src.write_text(SOURCE)
            subprocess.run(['clang++','--target=x86_64-pc-windows-msvc','-std=c++17', '-O2',
                '-funwind-tables','-ffreestanding','-fno-exceptions','-fno-rtti','-fno-stack-protector',
                f'-DVARIANT={i+2}','-c',str(src),'-o',str(obj)],check=True,timeout=30)
            subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib',
                '/export:shared_helper','/export:unique_helper',f'/out:{dll}',str(obj)],check=True,timeout=30)
        index=scan_modules(root)
        report=index['report']
        assert report['module_count']==3
        assert report['fingerprints_in_all_modules']>=1,report
        assert report['total_scoped_regions']>=6,report
        print('Owned three-PE shared executable region classification passed.',
            report['total_scoped_regions'],report['fingerprints_in_all_modules'])


if __name__=='__main__':main()
