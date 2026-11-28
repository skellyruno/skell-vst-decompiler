import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.anchor_survey import select_windows, survey


@unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE toolchain')
class SurveyTests(unittest.TestCase):
    def test_owned_unwind_extents(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            src=['.text','.globl entry','entry:','retq']
            for i in range(6):
                src += [f'.seh_proc fn{i}',f'fn{i}:','pushq %rbp','.seh_pushreg %rbp','.seh_endprologue']
                src += ['mulss %xmm1, %xmm0']*(4+i*4) if i else []
                src += ['.space 160, 0x90','popq %rbp','retq','.seh_endproc']
            (p/'f.s').write_text('\n'.join(src)+'\n')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/opt:noref',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe')
            r=survey(pe,pe.sha256,per_lane=2)
            self.assertEqual(r['runtime_records'],6)
            self.assertEqual(r['eligible_extents'],6)
            self.assertEqual(r['marker_positive_extents'],5)
            windows=r['windows']
            self.assertEqual(len({w['start'] for w in windows}),len(windows))
            self.assertEqual({w['lane'] for w in windows},{'stratified','marker_count','marker_density'})
            self.assertTrue(all(w['marker_count']==w['selected_fp_sites'] for w in windows))
            self.assertEqual(select_windows(pe,pe.sha256,per_lane=2),select_windows(pe,pe.sha256,per_lane=2))
            a=windows[0]['start']; b=a+windows[0]['bytes']
            r=select_windows(pe,pe.sha256,[(a,b)],per_lane=2)
            self.assertEqual(r['eligible_extents'],5)
            self.assertTrue(all(not (w['start']<b and a<w['start']+w['bytes']) for w in r['windows']))
            with self.assertRaises(PEFormatError): select_windows(pe,'0'*64)
            for invalid in (0,65,True):
                with self.assertRaises(ValueError): select_windows(pe,pe.sha256,per_lane=invalid)
            with self.assertRaises(ValueError): select_windows(pe,pe.sha256,[(5,4)])

    def test_shape_is_not_semantics(self):
        from skell_vst_decompiler.anchor_survey import shape_signature
        from skell_vst_decompiler.navigation import runtime_ranges
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            src=['.text','.globl entry','entry:','retq']
            for i in range(3):
                src += [f'.seh_proc fn{i}',f'fn{i}:','pushq %rbp','.seh_pushreg %rbp','.seh_endprologue',f'movl ${100+i}, %eax']
                src += [('mulss' if i<2 else 'addss')+' %xmm1, %xmm0']*20
                src += ['popq %rbp','retq','.seh_endproc']
            (p/'f.s').write_text('\n'.join(src)+'\n')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/opt:noref',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe'); extents=runtime_ranges(pe)
            hashes=[shape_signature(pe,pe.sha256,a,b-a) for a,b,_ in extents]
            self.assertTrue(all(hashes))
            self.assertEqual(hashes[0],hashes[1])  # differing immediates
            self.assertNotEqual(hashes[0],hashes[2])
            self.assertIsNone(shape_signature(pe,pe.sha256,extents[0][0],1))
            with self.assertRaises(PEFormatError): shape_signature(pe,'0'*64,extents[0][0],1)
            with self.assertRaises(ValueError): shape_signature(pe,pe.sha256,extents[0][0],8193)
