import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.mask_diagnostic import decode, scan
from skell_vst_decompiler.transfer_triage import parse_raw,raw_decode
from skell_vst_decompiler.pe import PE


class MaskTests(unittest.TestCase):
    def test_raw_forms(self):
        self.assertEqual(decode(bytes.fromhex('f30fc2e101')),('cmpltss',4,1))
        self.assertEqual(decode(bytes.fromhex('410f55f0')),('andnps',6,8))
        for s in ('f30fc2e1','f30fc2e108','f30fc20101','f30f54c1','0f55f000'):
            self.assertIsNone(decode(bytes.fromhex(s)))

    def test_complement_and_barriers(self):
        raw=bytes.fromhex('0fc2c1010f28d00f54c30f55d40f56c2')
        text='100: 0f c2 c1 01 \tcmpltps xmm0,xmm1\n104: 0f 28 d0 \tmovaps xmm2,xmm0\n107: 0f 54 c3 \tandps xmm0,xmm3\n10a: 0f 55 d4 \tandnps xmm2,xmm4\n10d: 0f 56 c2 \torps xmm0,xmm2'
        rows=parse_raw(text,raw,0x100)
        self.assertEqual(scan(rows,rows,raw,0x100)['complementary_mask_select_candidates'],1)
        self.assertNotIn('complementary_mask_select_candidates',scan(rows,rows,raw,0x100,entries={0x10a}))
        wrong=parse_raw(text.replace('andnps xmm2,xmm4','andnps xmm2,xmm5'),raw,0x100)
        self.assertNotIn('complementary_mask_select_candidates',scan(rows,wrong,raw,0x100))

    @unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')),'requires PE toolchain')
    def test_owned_select(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'f.s').write_text('''.text
.globl entry
entry:
 cmpltss %xmm1, %xmm0
 movaps %xmm0, %xmm2
 andps %xmm3, %xmm0
 andnps %xmm4, %xmm2
 orps %xmm2, %xmm0
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe');s=pe.section('.text');va=pe.image_base+s.rva;raw=pe.at_rva(s.rva,s.virtual_size,executable=True)
            a,b=[raw_decode(pe,s.rva,s.virtual_size,t) for t in ('objdump','llvm-objdump')]
            self.assertEqual(scan(a,b,raw,va),{'comparison_masks':1,'bitwise_register_ops':3,'complementary_mask_select_candidates':1,'select_ss':1})
