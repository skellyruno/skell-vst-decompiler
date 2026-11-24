import unittest
from skell_vst_decompiler.variant_navigation import inspect, overlaps


class VariantNavigationTest(unittest.TestCase):
    def test_overlap_is_fingerprint_scoped_and_half_open(self):
        def row(sha, start, end):
            return {'binary_sha256':sha,'report':'r.json','region':{'id':'r','start_rva':hex(start),'end_rva_exclusive':hex(end)}}
        rows=[row('a',0x100,0x110),row('b',0x110,0x120)]
        self.assertEqual(overlaps(rows,'a',0x110,0x120),[])
        self.assertEqual(overlaps(rows,'a',0x10f,0x120),['r.json::r'])

    def test_fingerprint_rejection_before_reading_binary(self):
        class FakePE:
            sha256='a'
        with self.assertRaises(ValueError):
            inspect(FakePE(),{'binary_sha256':'b','selected_plan':{'binary_sha256':'b'}},[])


if __name__=='__main__':unittest.main()
