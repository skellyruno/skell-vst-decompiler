import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
from skell_vst_decompiler.anchored_discovery import call_edges,processor_names,anchored
from skell_vst_decompiler.disasm import Instruction


class AnchoredTests(unittest.TestCase):
    def test_decoder_annotations_and_indirect_exclusion(self):
        pe=Mock(image_base=0x180000000)
        a=[Instruction(0x180001000,'call','0x180002000 <symbol+0x10>'),
           Instruction(0x180001005,'call','0x180003000'),
           Instruction(0x18000100a,'call','qword ptr [rax+0x20]')]
        self.assertEqual(list(call_edges(pe,a)),[{'site_rva':'0x1000','target_rva':'0x2000'},{'site_rva':'0x1005','target_rva':'0x3000'}])

    def test_exact_class_name(self):
        raw=b'.?AVTestAudioProcessor@@\0.?AVTestAudioProcessorEditor@@\0.?AVAudioProcessor@juce@@\0'
        pe=Mock(sections=[Mock(name='.data',executable=False,rva=4096,file_size=len(raw))])
        pe.sections[0].name='.data'
        pe.at_rva.return_value=raw
        self.assertEqual(processor_names(pe),['TestAudioProcessor'])

    def test_fallback_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'owned.dll';path.write_bytes(b'fixture')
            with patch('skell_vst_decompiler.anchored_discovery.PE'),patch('skell_vst_decompiler.anchored_discovery.runtime_ranges',return_value=[]),patch('skell_vst_decompiler.anchored_discovery.processor_names',return_value=[]),patch('skell_vst_decompiler.anchored_discovery.discover',return_value={'candidates':[]}) as fallback:
                self.assertEqual(anchored(path,8)['strategy'],'sampled_fallback_no_validated_processor_class')
                fallback.assert_called_once_with(path,limit=8,tool='objdump')

    def test_root_and_direct_callee(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'owned.dll';path.write_bytes(b'fixture')
            pe=Mock(image_base=0x180000000,sha256=hashlib.sha256(b'fixture').hexdigest())
            pe.at_rva.side_effect=lambda start,n,**kw:bytes(n)
            r={'start_rva':'0x1000','end_rva_exclusive':'0x1040','bytes':64}
            graph={'classes':[{'type':'.?AVTestAudioProcessor@@','vtables':[{'vtable_rva':'0x3000','hierarchy':{'base_records':[{'type':'.?AVAudioProcessor@juce@@'}]},'candidate_slots':[{'slot':7,'rva':'0x1000','unwind_region':r}]}]}]}
            def instructions(p,start,n,tool):
                seq=[Instruction(p.image_base+start+i*4,'mulss','xmm0, dword ptr [rax]') for i in range(4)]
                if start==0x1000:seq.append(Instruction(p.image_base+start+16,'call','0x180002000 <callee>'))
                return seq
            with patch('skell_vst_decompiler.anchored_discovery.PE',return_value=pe),patch('skell_vst_decompiler.anchored_discovery.runtime_ranges',return_value=[(0x1000,0x1040,1),(0x2000,0x2040,1)]),patch('skell_vst_decompiler.anchored_discovery.processor_names',return_value=['TestAudioProcessor']),patch('skell_vst_decompiler.anchored_discovery.class_graph',return_value=graph),patch('skell_vst_decompiler.anchored_discovery.disassemble',side_effect=instructions):
                report=anchored(path,8)
            self.assertEqual(report['scanned_records'],2)
            self.assertEqual(report['candidates'][0]['root_slots'][0]['slot'],7)
            self.assertEqual(report['candidates'][1]['depth'],1)
            self.assertEqual(report['direct_edges'][0]['containing_rva'],'0x2000')
