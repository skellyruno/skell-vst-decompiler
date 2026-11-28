import unittest
from skell_vst_decompiler.code_census import parse, compare


class CodeCensusTests(unittest.TestCase):
    def setUp(self):
        self.data=bytes.fromhex('e8 01 00 00 00 90 c3 d9 ee')
        self.gnu='1000: e8 01 00 00 00 call 0x1006\n1005: 90 nop\n1006: c3 ret\n1007: d9 ee fldz\n'
        self.llvm='1000: e8 01 00 00 00 calll 0x1006\n1005: 90 nop\n1006: c3 retl\n1007: d9 ee fldz\n'

    def test_verified_span_and_call(self):
        r=compare(self.data,0x1000,self.gnu,self.llvm)
        self.assertEqual(r['exact_span_agreement'],4)
        self.assertEqual(r['agreed_instruction_bytes'],9)
        self.assertEqual(r['direct_rel32_calls'],1)
        self.assertEqual(r['direct_targets_at_agreed_scope_locations'],1)
        self.assertEqual(r['x87_unprefixed'],1)

    def test_disagreement_not_counted_as_agreement(self):
        r=compare(self.data,0x1000,self.gnu,self.llvm.replace('1005: 90 nop\n',''))
        self.assertEqual(r['exact_span_agreement'],3)
        self.assertEqual(r['gnu_only_locations'],1)
        r=compare(self.data,0x1000,self.gnu,self.llvm.replace('1007: d9 ee fldz','1007: d9 unknown'))
        self.assertEqual(r['exact_span_agreement'],3)

    def test_mismatch_rejected(self):
        with self.assertRaises(ValueError):parse(self.gnu.replace('90 nop','91 nop'),0x1000,self.data)
        with self.assertRaises(ValueError):parse(self.gnu+'1005: 90 nop\n',0x1000,self.data)

    def test_fwait_alias_equivalence(self):
        raw=bytes.fromhex("9b db e2 c3")
        fused="1000: 9b db e2 fclex\n1003: c3 ret\n"
        split="1000: 9b wait\n1001: db e2 fnclex\n1003: c3 retl\n"
        for a,b in ((fused,split),(split,fused)):
            r=compare(raw,0x1000,a,b)
            self.assertEqual(r["fwait_equivalent_pairs"],1)
            self.assertEqual(r["different_span_at_shared_location"],1)
            self.assertEqual(r["exact_span_agreement"],1)
        self.assertEqual(compare(raw,0x1000,fused,split.replace("fnclex","unknown"))["fwait_equivalent_pairs"],0)

    def test_bounds_and_data_pseudoinstructions(self):
        r=parse(self.gnu+'1009: 90 nop\n',0x1000,self.data)
        self.assertEqual(len(r),4)
        self.assertEqual(parse('1000: e8 .byte 0xe8',0x1000,self.data),{})
        with self.assertRaises(ValueError):parse('',0,b'')


if __name__=='__main__':unittest.main()
