import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE, PEFormatError


@unittest.skipUnless(all(shutil.which(t) for t in ('clang', 'lld-link')), 'PE fixture tools required')
class ImportBoundsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        (d/'probe.s').write_text('.text\n.globl probe\nprobe:\n call *__imp_external(%rip)\n ret\n')
        (d/'ext.def').write_text('LIBRARY example.dll\nEXPORTS\n external\n')
        subprocess.run(['lld-link','/lib','/def:'+str(d/'ext.def'),'/machine:x64','/out:'+str(d/'ext.lib')],check=True)
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(d/'probe.s'),'-o',str(d/'probe.obj')],check=True)
        subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/export:probe','/out:'+str(d/'probe.dll'),str(d/'probe.obj'),str(d/'ext.lib')],check=True)
        self.p = PE(d/'probe.dll')

    def patch(self, rva, raw):
        # Only mutate owned fixture bytes in memory, not the input on disk.
        p = self.p
        s = next(s for s in p.sections if s.rva <= rva and rva + len(raw) <= s.rva+s.file_size)
        pos = s.file_offset+rva-s.rva
        p.data = p.data[:pos]+raw+p.data[pos+len(raw):]

    def test_adjacent_zero_only(self):
        p = self.p; actual,meta = p.audit_imports()
        self.assertEqual(meta['terminator'],'inside_directory')
        p.import_directory_size -= 20
        self.assertEqual(p.audit_imports(), (actual,{**meta,'declared_bytes':20,'terminator':'adjacent_null_compatibility'}))
        self.patch(p.import_directory_rva+20,b'\x01')
        with self.assertRaisesRegex(PEFormatError,'Missing ordinary import terminator'):
            p.imports()

    def test_declared_length_and_header_count(self):
        p = self.p
        for size in (0,19,21,5140):
            p.import_directory_size=size
            with self.assertRaises(PEFormatError):p.imports()
        b=bytearray(p.data);opt=struct.unpack_from('<I',b,60)[0]+24
        struct.pack_into('<I',b,opt+108,1)
        path=Path(self.tmp.name)/'count.dll';path.write_bytes(b)
        self.assertEqual(PE(path).imports(),{})

    def test_slot_and_ordinal_validation(self):
        p=self.p;r=p.import_directory_rva
        oft,_,_,_,iat=struct.unpack('<IIIII',p.at_rva(r,20))
        self.patch(r+16,struct.pack('<I',0x7fff0000))
        with self.assertRaises(PEFormatError):p.imports()
        self.patch(r+16,struct.pack('<I',iat))
        self.patch(oft,struct.pack('<Q',0x8000000000010005))
        with self.assertRaisesRegex(PEFormatError,'ordinal reserved bits'):p.imports()
        self.patch(oft,struct.pack('<Q',0x8000000000000005))
        self.assertEqual(p.imports()[iat]['symbol'],'#5')
