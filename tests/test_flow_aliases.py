import unittest
from skell_vst_decompiler.flow_aliases import reconcile


class FlowAliasTests(unittest.TestCase):
    def test_clear_split_fused(self):
        data=bytes.fromhex('90 9b db e2 90 c3')
        fused='1000: 90 nop\n1001: 9b db e2 fclex\n1004: 90 nop\n1005: c3 ret'
        split='1000: 90 nop\n1001: 9b fwait\n1002: db e2 fnclex\n1004: 90 nop\n1005: c3 retl'
        for a,b in ((fused,split),(split,fused)):
            r=reconcile(data,0x1000,a,b,[0x1000])
            self.assertEqual(r['alias_pairs'],1)
            self.assertEqual(r['raw']['possible_reached_bytes'],1)
            self.assertEqual(r['normalized']['possible_reached_bytes'],6)
            self.assertEqual(r['additional_reached_bytes'],5)

    def test_init_and_seed_at_split(self):
        data=bytes.fromhex('9b db e3 c3')
        a='1000: 9b db e3 finit\n1003: c3 ret'
        b='1000: 9b wait\n1001: db e3 fninit\n1003: c3 ret'
        r=reconcile(data,0x1000,a,b,[0x1001])
        self.assertEqual(r['alias_pairs'],1)
        self.assertEqual(r['raw']['possible_reached_bytes'],0)
        self.assertEqual(r['normalized']['possible_reached_bytes'],3)

    def test_wrong_mnemonic_or_interior(self):
        data=bytes.fromhex('9b db e2 c3')
        a='1000: 9b db e2 fclex\n1003: c3 ret'
        b='1000: 9b wait\n1001: db e2 unknown\n1003: c3 ret'
        self.assertEqual(reconcile(data,0x1000,a,b,[0x1000])['alias_pairs'],0)
        b=b.replace('unknown','fnclex')+'\n1002: e2 nop'
        self.assertEqual(reconcile(data,0x1000,a,b,[0x1000])['alias_pairs'],0)

    def test_source_mismatch_fails_closed(self):
        data=bytes.fromhex('9b db e2 c3')
        a='1000: 9b db e2 fclex\n1003: c3 ret'
        b='1000: 9b wait\n1001: db e3 fnclex\n1003: c3 ret'
        with self.assertRaises(ValueError):reconcile(data,0x1000,a,b,[0x1000])


if __name__=='__main__':unittest.main()
