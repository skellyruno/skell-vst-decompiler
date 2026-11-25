"""Compile and inspect an owned PE fixture; never execute it."""
import hashlib
import pathlib
import re
import subprocess
import tempfile
from skell_vst_decompiler.direct_caller_audit import audit

with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d); src=p/'fixture.c'; obj=p/'fixture.obj'; exe=p/'fixture.exe'; mp=p/'fixture.map'
    src.write_text('__declspec(noinline) int target(int a){return a+13;}\n__declspec(noinline) int caller(int a){volatile int b=a;return target(b)+target(b+1);}\nvoid entry(void){volatile int q=caller(3);(void)q;}\n')
    subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-c',str(src),'-o',str(obj)],check=True)
    subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/map:{mp}',f'/out:{exe}',str(obj)],check=True)
    target=int(re.search(r'\btarget\s+([0-9a-fA-F]+)',mp.read_text())[1],16)-0x140000000
    sha=hashlib.sha256(exe.read_bytes()).hexdigest()
    report=audit(exe,sha,{target:'owned_target'})
    assert report['targets']['owned_target']['confirmed_calls']==2,report
    try:audit(exe,'0'*64,{target:'owned_target'})
    except ValueError:pass
    else:raise AssertionError('wrong fingerprint accepted')
    print('OWNED_DIRECT_CALLER_SMOKE_PASS')
