import struct
import unittest
from skell_vst_decompiler.legacy_math_audit import imports,relocations,summarize_scope


class FakePE:
    def __init__(self):
        self.data=bytearray(4096)
        self.sections=[{'rva':0x1000,'size':len(self.data)}]
        self.dirs={1:(0x1000,40),5:(0x1100,12)}
        self.put(0x1000,struct.pack('<IIIII',0x1040,0,0,0x1080,0x1050))
        self.put(0x1040,struct.pack('<II',0x1090,0))
        self.put(0x1050,struct.pack('<II',0x1090,0))
        self.put(0x1080,b'owned.dll\0')
        self.put(0x1090,b'\0\0probe_math\0')
        self.put(0x1100,struct.pack('<IIHH',0x1000,12,0x3202,0))

    def put(self,rva,data):self.data[rva-0x1000:rva-0x1000+len(data)]=data
    def read(self,rva,n):
        if not 0<=rva-0x1000<=len(self.data)-n:raise ValueError('Bad RVA')
        return bytes(self.data[rva-0x1000:rva-0x1000+n])
    def directory(self,i):return self.dirs.get(i,(0,0))


class LegacyMathTests(unittest.TestCase):
    def test_metadata(self):
        p=FakePE();self.assertEqual(imports(p),({0x1050:('owned.dll','probe_math')},1))
        self.assertEqual(relocations(p),({0x1202},1))

    def test_invalid_relocation(self):
        p=FakePE();p.put(0x1108,struct.pack('<HH',0x3202,0x3202))
        with self.assertRaises(ValueError):relocations(p)
        p=FakePE();p.put(0x1108,struct.pack('<H',0x9202))
        with self.assertRaises(ValueError):relocations(p)

    def test_unterminated_import(self):
        p=FakePE();p.dirs[1]=(0x1000,20)
        with self.assertRaises(ValueError):imports(p)

    def test_calls_and_jumps_separate(self):
        raw=bytes.fromhex('ff 15 50 10 00 10 ff 25 50 10 00 10 c3')
        a='10001200: ff 15 50 10 00 10 call *0x10001050\n10001206: ff 25 50 10 00 10 jmp *0x10001050\n1000120c: c3 ret'
        b=a.replace('call ','calll ').replace('jmp ','jmpl ')
        r=summarize_scope(raw,0x10001200,0x10000000,a,b,{0x1050:('owned.dll','probe_math')},{0x1202,0x1208},allowed={'probe_math'})
        self.assertEqual(r['public_math_call_counts'],{'probe_math':1})
        self.assertEqual(r['public_math_jump_counts'],{'probe_math':1})
        r=summarize_scope(raw,0x10001200,0x10000000,a,b,{0x1050:('owned.dll','probe_math')},{0x1202})
        self.assertEqual(r['iat_candidates_without_relocation'],1)
        self.assertEqual(r['relocation_backed_iat_jumps'],0)
        self.assertEqual(r['public_math_call_counts'],{})
        with self.assertRaises(ValueError):summarize_scope(raw,0x10001200,0x10000000,a,b.replace('ff 15','ff 25'),{},set())

    def test_disputed_decode_not_admitted(self):
        raw=bytes.fromhex('ff 15 50 10 00 10')
        a='10001200: ff 15 50 10 00 10 call *0x10001050'
        r=summarize_scope(raw,0x10001200,0x10000000,a,a.replace('call','jmp'),{0x1050:('owned.dll','probe_math')},{0x1202})
        self.assertEqual(r['relocation_backed_iat_calls'],0)


if __name__=='__main__':unittest.main()
