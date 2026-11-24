import unittest
from skell_vst_decompiler.context_flow import compare_context, compare_alias_context


class ContextTests(unittest.TestCase):
    def test_branch_leaves_and_reenters_child(self):
        data=bytes.fromhex('eb 04 eb 02 90 c3 eb fc')
        full='1000: eb 04 jmp 0x1006\n1002: eb 02 jmp 0x1006\n1004: 90 nop\n1005: c3 ret\n1006: eb fc jmp 0x1004'
        small='1002: eb 02 jmp 0x1006\n1004: 90 nop\n1005: c3 ret'
        r=compare_context(data,0x1000,full,full,0x1002,4,small,small)
        self.assertEqual(r['local_reached_spans'],1)
        self.assertEqual(r['same_seed_enclosing']['additional_spans'],2)
        self.assertEqual(r['same_seed_enclosing']['additional_bytes'],2)
        self.assertEqual(r['enclosing_entry_seed']['reached_comparable_spans'],2)
        self.assertEqual(r['enclosing_entry_seed']['local_spans_not_confirmed'],1)

    def test_no_independent_boundary(self):
        data=bytes.fromhex('eb 00 c3')
        full='1000: eb 00 jmp 0x1002\n1002: c3 ret'
        small='1001: 00 add\n1002: c3 ret'
        r=compare_context(data,0x1000,full,full,0x1001,2,small,small)
        self.assertFalse(r['child_seed_agreed_in_enclosing'])
        self.assertEqual(r['comparable_spans'],1)
        self.assertEqual(r['same_seed_enclosing']['reached_comparable_spans'],0)
        self.assertEqual(r['enclosing_entry_seed']['reached_comparable_spans'],1)

    def test_call_not_traversed(self):
        data=bytes.fromhex('e8 01 00 00 00 c3 90 c3')
        rows='1000: e8 01 00 00 00 call 0x1006\n1005: c3 ret\n1006: 90 nop\n1007: c3 ret'
        r=compare_context(data,0x1000,rows,rows,0x1000,len(data),rows,rows)
        self.assertEqual(r['local_reached_spans'],2)
        self.assertEqual(r['same_seed_enclosing']['additional_spans'],0)

    def test_alias_context_separate_raw_counts(self):
        data=bytes.fromhex('9b db e2 90 c3')
        a='1000: 9b db e2 fclex\n1003: 90 nop\n1004: c3 ret'
        b='1000: 9b wait\n1001: db e2 fnclex\n1003: 90 nop\n1004: c3 ret'
        child='1003: 90 nop\n1004: c3 ret'
        r=compare_alias_context(data,0x1000,a,b,0x1003,2,child,child)
        self.assertEqual(r['raw']['enclosing_entry_seed']['reached_comparable_spans'],0)
        self.assertEqual(r['normalized']['enclosing_entry_seed']['reached_comparable_spans'],2)
        self.assertEqual(r['enclosing_alias_pairs'],1)

    def test_bounds_and_source_checks(self):
        data=b'\x90\xc3'; rows='1000: 90 nop\n1001: c3 ret'
        with self.assertRaises(ValueError):compare_context(data,0x1000,rows,rows,0x1001,2,rows,rows)
        with self.assertRaises(ValueError):compare_context(data,0x1000,rows,rows,0x1000,2,rows,rows.replace('90 nop','91 nop'))


if __name__=='__main__':unittest.main()
