import unittest
from skell_vst_decompiler.transfer_triage import parse_raw
from skell_vst_decompiler.window_reconcile import Window,reconcile_windows


def win(va,raw,text_a,text_b=None):
    raw=bytes.fromhex(raw)
    return Window(va,va+len(raw),(parse_raw(text_a,raw,va),parse_raw(text_a if text_b is None else text_b,raw,va)))


class WindowTests(unittest.TestCase):
    def test_cross_window_guard_and_duplicate(self):
        a=win(0x100,'eb0e','100: eb 0e \tjmp 0x110')
        b=win(0x110,'90c3','110: 90 \tnop\n111: c3 \tret')
        g,c=reconcile_windows([a,a,b])
        self.assertEqual(g,[set(),set(),{0x110}])
        self.assertEqual(c['unique_direct'],1)
        self.assertEqual(c['repeated_observations'],1)
        self.assertEqual(c['cross_window_guard_observations'],1)

    def test_disagreement_never_propagated(self):
        a=win(0x100,'eb0e','100: eb 0e \tjmp 0x110')
        b=win(0x100,'eb0e','100: eb 0e \tjmp 0x110','100: eb 0e \tjmp 0x111')
        dest=win(0x110,'90c3','110: 90 \tnop\n111: c3 \tret')
        g,c=reconcile_windows([a,b,dest])
        self.assertEqual(g,[set(),set(),set()])
        self.assertEqual(c['unique_disagreement'],1)

    def test_boundary_conflict_not_forced(self):
        a=win(0x100,'eb01906690c3','100: eb 01 \tjmp 0x103\n102: 90 66 90 \tnop\n105: c3 \tret')
        b=win(0x103,'6690c3','103: 66 90 \tnop\n105: c3 \tret')
        g,c=reconcile_windows([a,b])
        self.assertEqual(g,[set(),{0x103}])
        self.assertEqual(c['conflict_has_other_common_start'],1)
        with self.assertRaises(ValueError):reconcile_windows([Window(0,32769,({},{}))])

    def test_redundant_rex_display(self):
        from skell_vst_decompiler.window_reconcile import inspect
        a=win(0x100,'48ffe0','100: 48 ff e0 \trex.W jmp rax','100: 48 ff e0 \tjmp rax')
        self.assertEqual(inspect(a),{0x100:('indirect_register',None)})
        b=win(0x100,'48ff6028','100: 48 ff 60 28 \trex.W jmp QWORD PTR [rax+0x28]','100: 48 ff 60 28 \tjmp qword ptr [rax + 0x28]')
        self.assertEqual(inspect(b),{0x100:('indirect_memory',None)})
        c=win(0x100,'48ffe0','100: 48 ff e0 \trex.W jmp rcx','100: 48 ff e0 \tjmp rax')
        self.assertEqual(inspect(c),{0x100:('unreconciled',None)})
        d=win(0x100,'487501','100: 48 75 01 \trex.W jne 0x104','100: 48 75 01 \tjne 0x104')
        self.assertEqual(inspect(d),{0x100:('unreconciled',None)})

    def test_covered_but_missing_source(self):
        a=win(0x100,'eb0e','100: eb 0e \tjmp 0x110')
        b=win(0x100,'eb0e','')
        dest=win(0x110,'90c3','110: 90 \tnop\n111: c3 \tret')
        g,c=reconcile_windows([a,b,dest])
        self.assertEqual(g,[set(),set(),set()])

    def test_owned_pe_cross_window(self):
        import shutil, subprocess, tempfile
        from pathlib import Path
        from skell_vst_decompiler.pe import PE
        from skell_vst_decompiler.disasm import disassemble
        from skell_vst_decompiler.transfer_triage import raw_decode
        from skell_vst_decompiler.value_flow import scan
        if not all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')):
            self.skipTest('requires PE toolchain')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'f.s').write_text('''.text
.globl entry
entry:
 .byte 0xeb, 0x04
 movss (%rbx), %xmm0
 mulss %xmm1, %xmm0
 movss %xmm0, (%rbx)
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe');s=pe.section('.text');va=pe.image_base+s.rva
            windows=[]
            for start,length in [(s.rva,2),(s.rva+2,s.virtual_size-2)]:
                v=pe.image_base+start
                maps=tuple(raw_decode(pe,start,length,t) for t in ('objdump','llvm-objdump'))
                windows.append(Window(v,v+length,maps))
            guards,c=reconcile_windows(windows)
            self.assertEqual(guards,[set(),{va+6}])
            l,r=[disassemble(pe,s.rva+2,s.virtual_size-2,t) for t in ('objdump','llvm-objdump')]
            raw=pe.at_rva(s.rva+2,s.virtual_size-2,executable=True)
            self.assertEqual(scan(l,r,raw,va+2)['total'],1)
            self.assertEqual(scan(l,r,raw,va+2,entries=guards[1])['total'],0)
