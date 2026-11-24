import struct
import unittest
from skell_vst_decompiler.reccmp_compat import named_exports


class ExportCompatibilityTests(unittest.TestCase):
    def fixture(self):
        base=0x10000000
        b=bytearray(1024)
        struct.pack_into('<IIHHIIIIIII',b,0x40,0,0,0,0,0,1,2,3,0x100,0x200,0x300)
        struct.pack_into('<II',b,0x100,0x800,0x900)
        struct.pack_into('<III',b,0x200,0x350,0x360,0x370)
        struct.pack_into('<HHH',b,0x300,1,0,1)
        for off,name in [(0x350,b'alias'),(0x360,b'first'),(0x370,b'second')]:
            b[off:off+len(name)+1]=name+b'\0'
        def read(addr,n):
            start=addr-base
            if not 0<=start<=len(b) or start+n>len(b):raise ValueError('bounds')
            return b[start:start+n]
        def string(addr):
            start=addr-base
            return bytes(b[start:b.index(0,start)])
        return base,b,read,string

    def test_noncontiguous_aliases_and_reordered_ordinals(self):
        base,b,read,string=self.fixture()
        self.assertEqual(named_exports(read,string,base,base+0x40),[(base+0x900,b'alias'),(base+0x800,b'first'),(base+0x900,b'second')])

    def test_invalid_ordinal(self):
        base,b,read,string=self.fixture()
        struct.pack_into('<H',b,0x300,2)
        with self.assertRaises(ValueError):named_exports(read,string,base,base+0x40)

    def test_no_named_exports(self):
        base,b,read,string=self.fixture()
        struct.pack_into('<I',b,0x40+24,0)
        self.assertEqual(named_exports(read,string,base,base+0x40),[])


if __name__=='__main__':unittest.main()
