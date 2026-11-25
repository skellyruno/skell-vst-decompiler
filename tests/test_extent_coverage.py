import unittest
import struct
from skell_vst_decompiler.extent_coverage import coverage,intersect,inspect


def fixture(bits=64):
    b=bytearray(1024);b[:2]=b'MZ';struct.pack_into('<I',b,60,64);b[64:68]=b'PE\0\0'
    opt=240 if bits==64 else 224;fixed=112 if bits==64 else 96;o=88
    struct.pack_into('<HHIIIHH',b,68,0x8664 if bits==64 else 0x14c,1,0,0,0,opt,0)
    struct.pack_into('<H',b,o,0x20b if bits==64 else 0x10b)
    struct.pack_into('<I',b,o+fixed-4,16)
    struct.pack_into('<8sIIIIIIHHI',b,o+opt,b'.text',128,4096,256,512,0,0,0,0,0x60000020)
    if bits==64:
        struct.pack_into('<II',b,o+fixed+24,4200,12)
        struct.pack_into('<III',b,616,4096,4128,4220);b[636]=1
    return bytes(b)


class ExtentTests(unittest.TestCase):
    def test_union_counts(self):
        r=coverage([(10,20),(15,25),(30,35)],[(12,18),(18,22)])
        self.assertEqual(r['scope_sum_bytes'],25)
        self.assertEqual(r['unique_scope_bytes'],20)
        self.assertEqual(r['unique_covered_bytes'],10)
        self.assertEqual(r['sum_covered_bytes'],15)
        self.assertEqual(r['coverage_counts'],{'partial':2,'none':1})

    def test_adjacent_intervals(self):
        self.assertEqual(coverage([(1,7)],[(1,4),(4,7)])['coverage_counts'],{'full':1})
        self.assertEqual(intersect([(0,3)],[(3,5)]),[])

    def test_x64_padding_and_unwind(self):
        r=inspect(fixture(),[(4096,4144),(4196,4240)])
        self.assertEqual(r['raw_padding_bytes'],128)
        self.assertEqual(r['runtime_records'],1)
        self.assertEqual(r['mapped_bytes_without_runtime_record'],96)
        self.assertEqual(r['scope_runtime_coverage']['unique_covered_bytes'],32)
        self.assertEqual(r['scope_mapped_coverage']['coverage_counts'],{'full':1,'partial':1})

    def test_x86_not_missing_unwind(self):
        r=inspect(fixture(32))
        self.assertIsNone(r['scope_runtime_coverage'])
        self.assertIsNone(r['mapped_bytes_without_runtime_record'])

    def test_bad_metadata(self):
        with self.assertRaises(ValueError):inspect(fixture(),[(1,2)])
        with self.assertRaises(ValueError):coverage([(4,3)],[])
        b=bytearray(fixture());struct.pack_into('<I',b,620,5000)
        with self.assertRaises(ValueError):inspect(bytes(b))

if __name__=='__main__':unittest.main()
