import shutil,subprocess,tempfile,unittest,struct
from pathlib import Path
from skell_vst_decompiler.pe import PE,PEFormatError
from skell_vst_decompiler.boundary_paths import BoundaryAudit,delay_imports,transfer

class DelayTests(unittest.TestCase):
    def test_synthetic_directory(self):
        class Fake:
            def __init__(self):self.data=bytearray(2048)
            def _unpack(self,f,o):return struct.unpack_from(f,self.data,o)
            def at_rva(self,r,n,**kw):
                if r<0 or r+n>len(self.data):raise PEFormatError('unbacked')
                return self.data[r:r+n]
            def cstring_rva(self,r):return self.data[r:].split(b'\0',1)[0].decode()
        p=Fake();struct.pack_into('<I',p.data,60,64);opt=88
        struct.pack_into('<H',p.data,opt-4,240);struct.pack_into('<I',p.data,opt+108,16);struct.pack_into('<II',p.data,opt+112+13*8,512,64)
        struct.pack_into('<8I',p.data,512,1,640,0,768,896,0,0,0);p.data[640:652]=b'example.dll\0';struct.pack_into('<QQQ',p.data,896,1024,0x8000000000000005,0);p.data[1026:1030]=b'foo\0'
        self.assertEqual(delay_imports(p),{768:{'dll':'example.dll','symbol':'foo','kind':'delay'},776:{'dll':'example.dll','symbol':'#5','kind':'delay'}})
        struct.pack_into('<I',p.data,512,0)
        with self.assertRaises(PEFormatError):delay_imports(p)
        struct.pack_into('<I',p.data,512,1);struct.pack_into('<I',p.data,opt+112+13*8+4,32)
        with self.assertRaises(PEFormatError):delay_imports(p)

@unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')),'PE fixture tools required')
class BoundaryTests(unittest.TestCase):
    def test_owned_jump_chain(self):
        asm='''.text
.globl probe
.seh_proc probe
probe:
 .seh_endprologue
 call a
 call *__imp_external(%rip)
 call local
 ret
.seh_endproc
a:
 jmp b
b:
 jmp *__imp_external(%rip)
local:
 ret
cycle:
 jmp cycle
'''
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'probe.s').write_text(asm);(d/'ext.def').write_text('LIBRARY example.dll\nEXPORTS\n external\n')
            subprocess.run(['lld-link','/lib','/def:'+str(d/'ext.def'),'/machine:x64','/out:'+str(d/'ext.lib')],check=True)
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(d/'probe.s'),'-o',str(d/'probe.obj')],check=True)
            subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/export:probe','/out:'+str(d/'probe.dll'),str(d/'probe.obj'),str(d/'ext.lib')],check=True)
            from skell_vst_decompiler.navigation import runtime_ranges
            p=PE(d/'probe.dll');start,end,_=runtime_ranges(p)[0];a=BoundaryAudit(p);r=a.scope(start,end-start)
            self.assertEqual(r['counts'],{'import_boundary':2,'local_entry':1});self.assertEqual(r['rejected'],0)
            self.assertEqual(len(r['import_edges'][0]['hops']),2);self.assertEqual(len(r['import_edges'][1]['hops']),0)
            self.assertEqual(r['import_edges'][0]['symbol'],'external');self.assertEqual(a.follow(int(r['import_edges'][0]['hops'][0],16),1)['status'],'hop_limit')
            self.assertIsNone(transfer(p,start,start+1));self.assertEqual(a.follow(-1)['status'],'outside_executable')
            # Exact cycle instruction in owned fixture; no arbitrary binary execution.
            sec=p.section('.text');i=p.at_rva(sec.rva,sec.file_size).find(b'\xeb\xfe');self.assertGreaterEqual(i,0);self.assertEqual(a.follow(sec.rva+i)['status'],'cycle')

    def test_linked_delay_import(self):
        asm='''.text
.globl probe
.seh_proc probe
probe:
 .seh_endprologue
 call *__imp_external(%rip)
 ret
.seh_endproc
.globl __delayLoadHelper2
__delayLoadHelper2:
 xor %eax,%eax
 ret
'''
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'probe.s').write_text(asm);(d/'ext.def').write_text('LIBRARY example.dll\nEXPORTS\n external\n')
            subprocess.run(['lld-link','/lib','/def:'+str(d/'ext.def'),'/machine:x64','/out:'+str(d/'ext.lib')],check=True)
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(d/'probe.s'),'-o',str(d/'probe.obj')],check=True)
            subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/export:probe','/delayload:example.dll','/out:'+str(d/'probe.dll'),str(d/'probe.obj'),str(d/'ext.lib')],check=True)
            p=PE(d/'probe.dll');a=BoundaryAudit(p)
            self.assertEqual(list(a.imports.values()),[{'dll':'example.dll','symbol':'external','kind':'delay'}])
            from skell_vst_decompiler.navigation import runtime_ranges
            start,end,_=runtime_ranges(p)[0];r=a.scope(start,end-start)
            self.assertEqual(r['counts'],{'import_boundary':1});self.assertEqual(r['import_edges'][0]['kind'],'delay')
