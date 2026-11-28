import struct
import unittest
from skell_vst_decompiler.unwind_chain import summarize


def fixture(mode='valid',bits=64):
    b=bytearray(2048);b[:2]=b'MZ';struct.pack_into('<I',b,60,64);b[64:68]=b'PE\0\0';o=88
    opt=240 if bits==64 else 224;fixed=112 if bits==64 else 96
    struct.pack_into('<HHIIIHH',b,68,0x8664 if bits==64 else 0x14c,1,0,0,0,opt,0)
    struct.pack_into('<H',b,o,0x20b if bits==64 else 0x10b);struct.pack_into('<I',b,o+fixed-4,16)
    struct.pack_into('<8sIIIIIIHHI',b,o+opt,b'.text',1024,4096,1024,512,0,0,0,0,0x60000020)
    if bits==32:return bytes(b)
    records=[(4096,4112,4352),(4112,4128,4384),(4128,4144,4416)]
    struct.pack_into('<II',b,o+fixed+24,4224,36)
    for i,r in enumerate(records):struct.pack_into('<III',b,640+12*i,*r)
    b[768]=1;b[800]=33;b[832]=33;b[802]=1
    struct.pack_into('<III',b,808,*records[0]);struct.pack_into('<III',b,836,*records[1])
    if mode=='cycle':struct.pack_into('<III',b,808,*records[2])
    elif mode=='missing':struct.pack_into('<III',b,808,4096,4112,4400)
    elif mode=='bad_flags':b[800]=41
    return bytes(b)


class ChainTests(unittest.TestCase):
    def test_resolved_and_padded(self):
        r=summarize(fixture());self.assertEqual(r['outcomes'],{'resolved_table_root':2});self.assertEqual(r['resolved_depth_histogram'],{1:1,2:1});self.assertEqual(r['distinct_resolved_roots'],1)
    def test_cycles_and_missing(self):
        self.assertEqual(summarize(fixture('cycle'))['outcomes'],{'cycle':2});self.assertEqual(summarize(fixture('missing'))['outcomes'],{'parent_not_in_table':2})
    def test_invalid_flags_and_x86(self):
        r=summarize(fixture('bad_flags'));self.assertEqual(r['invalid_chain_metadata'],1);self.assertEqual(r['outcomes'],{'unresolved_terminal':1});self.assertFalse(summarize(fixture(bits=32))['applicable'])


if __name__=='__main__':unittest.main()
