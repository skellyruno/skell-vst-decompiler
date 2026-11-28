import unittest
from skell_vst_decompiler.static_flow import summarize


class FlowTests(unittest.TestCase):
    def test_unconditional_skips_data_and_call_not_followed(self):
        data=bytes.fromhex('eb 02 90 c3 e8 f9 ff ff ff c3')
        rows='1000: eb 02 jmp 0x1004\n1002: 90 nop\n1003: c3 ret\n1004: e8 f9 ff ff ff call 0x1002\n1009: c3 ret\n'
        r=summarize(data,0x1000,rows,rows,[0x1000])
        self.assertEqual(r['possible_reached_spans'],3)
        self.assertEqual(r['not_reached_in_model'],2)
        self.assertEqual(r['direct_call_destinations_not_followed'],{'agreed_start':1})
        self.assertEqual(r['instruction_categories']['return'],1)

    def test_conditional_both_arms_and_loop_termination(self):
        data=bytes.fromhex('74 02 eb fc c3')
        rows='1000: 74 02 je 0x1004\n1002: eb fc jmp 0x1000\n1004: c3 ret\n'
        r=summarize(data,0x1000,rows,rows,[0x1000])
        self.assertEqual(r['possible_reached_spans'],3)
        self.assertEqual(r['flow_destinations'],{'agreed_start':3})

    def test_interior_boundary_and_indirect_stop(self):
        data=bytes.fromhex('74 ff ff e0 90 c3')
        rows='1000: 74 ff je 0x1001\n1002: ff e0 jmp *%eax\n1004: 90 nop\n1005: c3 ret\n'
        r=summarize(data,0x1000,rows,rows,[0x1000])
        self.assertEqual(r['possible_reached_spans'],2)
        self.assertEqual(r['flow_destinations']['interior_of_span'],1)
        self.assertEqual(r['instruction_categories']['indirect_jump'],1)

    def test_missing_and_external_boundaries(self):
        data=bytes.fromhex('74 04 90 c3')
        rows='1000: 74 04 je 0x1006\n1002: 90 nop\n1003: c3 ret\n'
        r=summarize(data,0x1000,rows,rows.replace('1002: 90 nop\n',''),[0x1000])
        self.assertEqual(r['flow_destinations'],{'outside_scope':1,'unverified_boundary':1})
        self.assertEqual(r['possible_reached_spans'],1)

    def test_exact_x64_rex_stack_alias(self):
        data=bytes.fromhex('40 53 c3')
        a='1000: 40 53 rex push %rbx\n1002: c3 ret\n'
        b='1000: 40 53 pushq %rbx\n1002: c3 retq\n'
        self.assertEqual(summarize(data,0x1000,a,b,[0x1000],bits=64)['possible_reached_spans'],2)
        self.assertEqual(summarize(data,0x1000,a,b,[0x1000],bits=32)['possible_reached_spans'],1)
        self.assertEqual(summarize(data,0x1000,a,b.replace('pushq','jmp'),[0x1000],bits=64)['possible_reached_spans'],1)

    def test_invalid_and_disputed(self):
        data=bytes.fromhex('90 c3')
        rows='1000: 90 nop\n1001: c3 ret\n'
        with self.assertRaises(ValueError):summarize(data,0x1000,rows,rows.replace('90 nop','91 nop'),[0x1000])
        with self.assertRaises(ValueError):summarize(data,0x1000,rows,rows,[0x1002])
        r=summarize(data,0x1000,rows,rows.replace('nop','jmp'),[0x1000])
        self.assertEqual(r['instruction_categories'],{'barrier':1})

if __name__=='__main__':unittest.main()
