"""Owned PE ground truth: unwind scope plus address-taken leaf and data."""
import pathlib
import subprocess
import tempfile
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.coverage_audit import coverage
from skell_vst_decompiler.relocation_navigation import census
with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d); src=p/'f.c'; obj=p/'f.obj'; exe=p/'f.exe'
    src.write_text('''
__declspec(noinline) int leaf(int x){return x*3;}
__declspec(noinline) int nonleaf(int x){volatile int v=x;return leaf(v)+leaf(v+1);}
typedef int (*Fn)(int);
Fn volatile callbacks[]={leaf,nonleaf,leaf};
int data=3; int* volatile ptr=&data;
void entry(void){volatile int x=callbacks[0](*ptr);(void)x;}
''')
    subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-c',str(src),'-o',str(obj)],check=True)
    subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{exe}',str(obj)],check=True)
    sha=PE(exe).sha256; a=coverage(exe,sha); b=census(exe,sha,{})
    assert a['categories']==b['categories'],a
    assert a['unique_code_targets']==2 and a['unique_targets_without_unwind']==1,a
    assert a['categories']=={'no_unwind_range':2,'non_code_target':1,'unwind_start':1},a
    assert 0<a['unwind_covered_bytes']<a['executable_virtual_file_bytes'],a
    try:coverage(exe,'0'*64)
    except ValueError:pass
    else:raise AssertionError('incorrect SHA accepted')
    print('OWNED_COVERAGE_PASS',a)
