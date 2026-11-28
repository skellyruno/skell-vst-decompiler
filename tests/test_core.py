import math
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.disasm import Instruction, parse_disassembly, direct_calls, disassemble
from skell_vst_decompiler.equations import (
    IndependentDF2T, verify_tvb_first_biquad, TVB_COMPRESSOR_FIRST_BIQUAD, TVB_SHA256
)


def synthetic_pe():
    b=bytearray(1024)
    b[:2]=b'MZ';struct.pack_into('<I',b,0x3C,0x80)
    b[0x80:0x84]=b'PE\x00\x00'
    struct.pack_into('<HH',b,0x84,0x8664,1)
    struct.pack_into('<H',b,0x84+16,0xF0)
    opt=0x98
    struct.pack_into('<H',b,opt,0x20b)
    struct.pack_into('<Q',b,opt+24,0x180000000)
    pos=opt+0xF0
    struct.pack_into('<8sIIIIIIHHI',b,pos,b'.text\x00\x00\x00',0x100,0x1000,0x100,0x300,0,0,0,0,0x60000020)
    b[0x300:0x304]=b'\x90\x90\x90\xc3'
    return b

class TestCore(unittest.TestCase):
    def test_valid_pe_and_rva(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'sample.vst3';p.write_bytes(synthetic_pe())
            x=PE(p);self.assertEqual(x.at_rva(0x1000,4),b'\x90\x90\x90\xc3')
            self.assertTrue(x.section('.text').executable)
            self.assertEqual(x.inventory()['sections'][0]['rva'],'0x1000')
            with self.assertRaises(PEFormatError):x.at_rva(0x2000,1)
    def test_reject_corrupt_files(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad.bin';p.write_bytes(b'meow')
            with self.assertRaises(PEFormatError):PE(p)
            b=synthetic_pe();struct.pack_into('<I',b,0x3c,0xFFFFFF00);p.write_bytes(b)
            with self.assertRaises(PEFormatError):PE(p)
            b=synthetic_pe();struct.pack_into('<I',b,0x98+0xF0+20,2000);p.write_bytes(b)
            with self.assertRaises(PEFormatError):PE(p)
    def test_parse_objdump_and_call(self):
        s='''00000001805d07bf <.text+0x5cf7bf>:\n   1805d07bf:\tmovaps xmm2,xmm7\n   1805d07c6:\tmulss  xmm2,DWORD PTR [rsi+0x520]\n   1805d07ca:\tcall   0x18015f0d0\n'''
        ins=parse_disassembly(s)
        self.assertEqual(len(ins),3)
        self.assertEqual(ins[1].operands,'xmm2,DWORD PTR [rsi+0x520]')
        class Dummy: image_base=0x180000000
        self.assertEqual(direct_calls(Dummy(),ins),[{'site_rva':'0x5d07ca','target_rva':'0x15f0d0'}])
    def test_opcode_proof_requires_all_instructions(self):
        bs=TVB_COMPRESSOR_FIRST_BIQUAD['required']
        ins=[Instruction(0x180000000+rva,mnem,ops) for rva,mnem,ops in bs]
        proved=verify_tvb_first_biquad(ins,0x180000000,TVB_SHA256)
        self.assertIn('b0*x',proved['math'][0])
        with self.assertRaises(ValueError):verify_tvb_first_biquad(ins[:-1],0x180000000,TVB_SHA256)
        with self.assertRaises(ValueError):verify_tvb_first_biquad(ins,0x180000000,'wrong-build-hash')
        mutated=list(ins);mutated[3]=Instruction(mutated[3].address,'addss',mutated[3].operands)
        with self.assertRaises(ValueError):verify_tvb_first_biquad(mutated,0x180000000,TVB_SHA256)
    def test_independent_biquad_impulse_and_blocks(self):
        def run(groups):
            f=IndependentDF2T(.5,.25,.125,-.3,.1)
            result=[]
            data=[1.0]+[0.0]*99
            off=0
            for n in groups:
                result += [f.process(x) for x in data[off:off+n]]
                off+=n
            return result
        a=run([100]);b=run([7,33,60])
        self.assertEqual(a,b)
        self.assertEqual(a[0],.5)
        self.assertAlmostEqual(a[1],.4,places=12)
        self.assertTrue(all(math.isfinite(x) for x in a))

if __name__ == '__main__':unittest.main()

class TestTraceSafety(unittest.TestCase):
    def test_rip_refs_skip_nonfloat_and_report_nan_as_null(self):
        from skell_vst_decompiler.disasm import rip_data_refs
        class P:
            image_base=0x180000000
            def at_rva(self,rva,n):
                if rva!=0x1230 or n!=4: raise PEFormatError('not backed')
                return b'\x00\x00\xc0\x7f' # quiet NaN
        addr=0x180000000+0x4321
        ins=[Instruction(addr,'lea','rcx,[rip+0x1] # 0x180001230'),
             Instruction(addr+5,'movss','xmm0,DWORD PTR [rip+0x1] # 0x180001230')]
        values=rip_data_refs(P(),ins)
        self.assertEqual(len(values),1)
        self.assertIsNone(values[0]['float32_candidate'])
        import json
        json.dumps(values,allow_nan=False)

    def test_full_biquad_bank_structure(self):
        from skell_vst_decompiler.equations import trace_tvb_biquad_bank, TVB_SHA256
        from unittest.mock import patch
        source=TVB_COMPRESSOR_FIRST_BIQUAD['required']
        ins=[Instruction(0x180000000+addr,op,args) for addr,op,args in source]
        ins += [Instruction(0x180000000+0x5d07c2,'lea','rax,[rbx+rbx*2]'),
                Instruction(0x180000000+0x5d07d1,'shl','rax,0x6')]
        for idx in range(24):
            for j in range(5):
                ins.append(Instruction(0x180000000+0x5d0830+idx*25+j,
                      'mulss',f'xmm1,DWORD PTR [rsi+{hex(0x520+idx*20+j*4)}]'))
            for j in range(2):
                ins.append(Instruction(0x180000000+0x5d0835+idx*25+j,
                      'movss',f'DWORD PTR [rax+rsi*1+{hex(0x718+idx*8+j*4)}],xmm1'))
        class P:sha256=TVB_SHA256;image_base=0x180000000
        with patch('skell_vst_decompiler.equations.disassemble',return_value=ins):
            result=trace_tvb_biquad_bank(P())
            self.assertEqual(result['stage_count'],24)
            self.assertEqual(result['channel_state_stride_bytes'],192)
            bad=[v for v in ins if 'rsi+0x6fc' not in v.operands]
            with patch('skell_vst_decompiler.equations.disassemble',return_value=bad):
                with self.assertRaises(ValueError):trace_tvb_biquad_bank(P())

class TestImportResolver(unittest.TestCase):
    def test_cstring_near_section_end(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'synthetic.vst3'
            raw=synthetic_pe()
            raw[0x3fa:0x400]=b'abcde\x00'
            p.write_bytes(raw)
            self.assertEqual(PE(p).cstring_rva(0x10fa),'abcde')

    def test_direct_call_import_thunk(self):
        from skell_vst_decompiler.disasm import imported_call_sites
        class P:
            image_base=0x180000000
            def imports(self):return {0x3000:{'dll':'test-math.dll','symbol':'expf'}}
            def at_rva(self,rva,n,executable=False):
                self_last = rva == 0x1100 and n==6 and executable
                if not self_last:raise PEFormatError('not a code thunk')
                # ff 25 + relative displacement to IAT 0x3000
                return b'\xff\x25'+struct.pack('<i',0x3000-(rva+6))
        ins=[Instruction(0x180001080,'call','0x180001100')]
        r=imported_call_sites(P(),ins)
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]['symbol'],'expf')
        self.assertEqual(r[0]['iat_rva'],'0x3000')
