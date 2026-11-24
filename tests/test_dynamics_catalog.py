import math
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch
from skell_vst_decompiler.catalog import search
from skell_vst_decompiler.dispatch import trace_dispatch
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.dynamics import verify_dynamics
from skell_vst_decompiler.pe import PEFormatError

# Public, textbook dynamics mathematics; not a recovered vendor implementation.
class TestMath(unittest.TestCase):
    def test_soft_knee_value_and_slope(self):
        k=6.; ratio=4.; slope=1-1/ratio
        def knee(u):
            if u<=-k/2: return 0.
            if u>=k/2: return slope*u
            return slope*(u+k/2)**2/(2*k)
        self.assertAlmostEqual(knee(0),.5625)
        self.assertAlmostEqual(knee(12),9.)
        self.assertAlmostEqual(10**(-knee(12)/20),.35481338923357547)
        for b,expected in [(-k/2,0.),(k/2,slope)]:
            h=1e-5
            self.assertAlmostEqual((knee(b+h)-knee(b-h))/(2*h),expected,places=5)
    def test_one_pole_recovery_across_rates(self):
        for sr in (44100,48000,96000,192000):
            for t in (.08,.3,1.5):
                alpha=-math.expm1(-1/(t*sr));state=12.
                for _ in range(round(sr*t)):state += alpha*(0-state)
                self.assertAlmostEqual(state,12/math.e,places=9)
    def test_dual_envelope_sustained_vs_short(self):
        def response(n):
            sr=48000; fast=slow=0.;
            for i in range(n+24000):
                target=12 if i<n else 0
                fast+=-math.expm1(-1/(sr*(.003 if target>fast else .08)))*(target-fast)
                slow+=-math.expm1(-1/(sr*(.3 if target>slow else 1.5)))*(target-slow)
            return max(fast,slow)
        self.assertGreater(response(48000),response(2400)*5)

class TestCatalog(unittest.TestCase):
    def setUp(self):
        self.report=json.loads((Path(__file__).resolve().parents[1]/'reports/tvb_dynamics_equations.json').read_text())
    def test_query_and_exact_half_open_rva(self):
        self.assertEqual(search(self.report,'0x5d1b35')['matches'][0]['id'],'mode0_knee')
        self.assertEqual(search(self.report,'0x5d1bac')['matches'][0]['id'],'dual_recovery')
        self.assertGreaterEqual(len(search(self.report,'gain reduction')['matches']),3)
        self.assertEqual(search(self.report,'no-such-equation')['matches'],[])
        with self.assertRaises(ValueError):search(self.report,'0xgarbage')
    def test_unknown_binary_fails_before_disassembly(self):
        class P:sha256='wrong'
        with patch('skell_vst_decompiler.dynamics.disassemble') as d:
            with self.assertRaises(ValueError):verify_dynamics(P())
            d.assert_not_called()
    def test_dispatch_targets_not_runtime_choice(self):
        class P:
            sha256='test';image_base=0x180000000;path=Path('synthetic.epl')
            def at_rva(self,rva,n,executable=False):
                if executable and rva==0x5000 and n==1:return b'\xc3'
                if not executable and rva in (0x3000,0x3008) and n==8:
                    return struct.pack('<Q',self.image_base+(0x5000 if rva==0x3000 else 0x6000))
                raise PEFormatError('not backed')
        ins=[Instruction(0x180001000,'movsxd','rax,DWORD PTR [rip+0x10] # 0x180002000'),Instruction(0x180001007,'lea','r11,[rip+0x20] # 0x180003000'),Instruction(0x18000100e,'jmp','QWORD PTR [r11+rax*8]')]
        with patch('skell_vst_decompiler.dispatch.disassemble',return_value=ins):
            result=trace_dispatch(P(),0x1000,2)
            self.assertFalse(result['selector_file_backed'])
            self.assertEqual(result['sampled_slots'][0]['target_rva'],'0x5000')
            self.assertIsNone(result['sampled_slots'][1]['target_rva'])
            with self.assertRaises(ValueError):trace_dispatch(P(),0x1000,33)
        with patch('skell_vst_decompiler.dispatch.disassemble',return_value=ins[:2]):
            with self.assertRaises(ValueError):trace_dispatch(P(),0x1000,2)
