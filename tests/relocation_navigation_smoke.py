"""Compile a source-known PE and check absolute code pointer vs data references."""
import hashlib
import pathlib
import re
import struct
import subprocess
import tempfile
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.relocation_navigation import census, relocated_slots

with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d); src=p/'fixture.c'; obj=p/'fixture.obj'; exe=p/'fixture.exe'; mp=p/'fixture.map'
    src.write_text('''
__declspec(noinline) int helper(int x){return x+1;}
__declspec(noinline) int target(int x){volatile int v=x;return helper(v)+helper(v+2);}
__declspec(noinline) int other(int x){return x*5;}
typedef int (*Fn)(int);
Fn volatile callbacks[]={target,other,target};
int data=3; int* volatile dataPointer=&data;
void entry(void){volatile int x=callbacks[0](*dataPointer);(void)x;}
''')
    subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-c',str(src),'-o',str(obj)],check=True)
    subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/map:{mp}',f'/out:{exe}',str(obj)],check=True)
    pe=PE(exe)
    def rva(name):return int(re.search(r'\b'+name+r'\s+([0-9a-fA-F]+)',mp.read_text())[1],16)-pe.image_base
    report=census(exe,pe.sha256,{'target':rva('target'),'leaf':rva('other'),'interior':rva('target')+1})
    assert report['relocation_slots']==4,report
    assert report['anchors']['target']['exact_anchor_slots']==2,report
    assert report['anchors']['target']['scope_start_slots']==2,report
    assert report['anchors']['leaf']['exact_anchor_slots']==1,report
    assert report['anchors']['interior']['exact_anchor_slots']==0,report
    assert report['anchors']['interior']['scope_start_slots']==2,report
    assert report['categories']['non_code_target']==1,report
    try:census(exe,'0'*64,{})
    except ValueError:pass
    else:raise AssertionError('wrong hash accepted')
    section=pe.section('.reloc'); assert section
    # Set the first block size to an invalid value; parser must reject even if the new SHA is supplied.
    bad=bytearray(exe.read_bytes());struct.pack_into('<I',bad,section.file_offset+4,7)
    invalid=p/'invalid.exe';invalid.write_bytes(bad)
    try:census(invalid,hashlib.sha256(bad).hexdigest(),{})
    except PEFormatError:pass
    else:raise AssertionError('malformed relocation block accepted')
    assert len(relocated_slots(pe))==4
    print('OWNED_RELOCATION_SMOKE_PASS: 4 relocations, 3 code pointers, 1 data pointer, interior and malformed controls')
