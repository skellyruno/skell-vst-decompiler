import struct
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.legacy_pe import LegacyPE


def fixture():
    b=bytearray(1024);b[:2]=b'MZ';struct.pack_into('<I',b,60,128);b[128:132]=b'PE\0\0'
    struct.pack_into('<HHIIIHH',b,132,0x14c,1,0,0,0,224,0x2102)
    opt=152;struct.pack_into('<H',b,opt,0x10b);struct.pack_into('<I',b,opt+28,0x10000000)
    struct.pack_into('<I',b,opt+92,16);struct.pack_into('<II',b,opt+96,0x1000,0x80)
    struct.pack_into('<8sIIIIIIHHI',b,opt+224,b'.text\0\0\0',512,0x1000,512,512,0,0,0,0,0x60000020)
    struct.pack_into('<IIHHIIIIIII',b,512,0,0,0,0,0,1,1,1,0x1040,0x1044,0x1048)
    struct.pack_into('<IIH',b,576,0x1100,0x1050,0);b[592:606]=b'VSTPluginMain\0'
    return b


class LegacyPETest(unittest.TestCase):
    def test_public_export(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.dll';p.write_bytes(fixture());r=LegacyPE(p).inventory()
            self.assertEqual(r['architecture'],'x86');self.assertTrue(r['dll'])
            self.assertEqual(r['exports']['public_vst_entries'],[{'name':'VSTPluginMain','rva':'0x1100','forwarded':False}])
            self.assertFalse(r['has_exception_directory'])

    def test_malformed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.dll'
            for off,fmt,value in [(132,'<H',0x8664),(152+92,'<I',100),(152+224+20,'<I',9999),(584,'<H',3)]:
                b=fixture();struct.pack_into(fmt,b,off,value);p.write_bytes(b)
                with self.assertRaises(ValueError):LegacyPE(p).inventory()

if __name__=='__main__':unittest.main()
