import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from skell_vst_decompiler.dsp_job import run_job

class DSPJobTests(unittest.TestCase):
    def test_new_report_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'report.json';binary=root/'fixture.dll'
            with patch('skell_vst_decompiler.dsp_job.shutil.which',return_value='/bin/objdump'),patch('skell_vst_decompiler.dsp_job.discover',return_value={'type':'dsp_discovery'}) as scan:
                self.assertEqual(run_job(binary,out),0)
                scan.assert_called_once_with(binary,limit=64,tool='objdump')
                self.assertEqual(json.loads(out.read_text())['type'],'dsp_discovery')
                with self.assertRaises(ValueError):run_job(binary,out)
    def test_error_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'error.json'
            with patch('skell_vst_decompiler.dsp_job.shutil.which',return_value=None):
                self.assertEqual(run_job(root/'fixture.dll',out),1)
            self.assertEqual(json.loads(out.read_text())['type'],'dsp_discovery_error')

    def test_shared_corpus_annotation_preserves_own_rank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=root/'fixture.epl';out=root/'annotated.json';corpus=root/'engines';corpus.mkdir()
            sample={'type':'dsp_discovery','binary_sha256':'a'*64,'candidates':[{'start_rva':'0x100','end_rva_exclusive':'0x180','status':'CANDIDATE','score':90}]}
            summary={'report':{'module_count':31,'region_limits':[32,4096],'total_scoped_regions':300,'fingerprints_in_all_modules':10,'regions_matching_at_least_10_modules':77}}
            with patch('skell_vst_decompiler.dsp_job.shutil.which',return_value='/bin/objdump'),\
                 patch('skell_vst_decompiler.dsp_job.discover',return_value=sample),\
                 patch('skell_vst_decompiler.dsp_job.scan_modules',return_value=summary) as scan,\
                 patch('skell_vst_decompiler.dsp_job.annotate_shared',return_value=[{**sample['candidates'][0],'cross_module_evidence':{'module_frequency':1}}]) as ann:
                self.assertEqual(run_job(binary,out,shared_corpus=corpus),0)
                scan.assert_called_once_with(corpus)
                ann.assert_called_once()
                report=json.loads(out.read_text())
                self.assertEqual(report['shared_code_context']['modules'],31)
                self.assertEqual(report['candidates'][0]['score'],90)
                self.assertEqual(report['candidates'][0]['cross_module_evidence']['module_frequency'],1)

    def test_no_silent_fallback_when_target_not_in_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=root/'x.epl';out=root/'error.json'
            with patch('skell_vst_decompiler.dsp_job.shutil.which',return_value='/bin/objdump'),\
                 patch('skell_vst_decompiler.dsp_job.discover',return_value={'binary_sha256':'0'*64,'candidates':[]}),\
                 patch('skell_vst_decompiler.dsp_job.scan_modules',return_value={'report':{},'modules':{}}),\
                 patch('skell_vst_decompiler.dsp_job.annotate_shared',side_effect=ValueError('Target not in corpus')):
                self.assertEqual(run_job(binary,out,shared_corpus=root),1)
            self.assertEqual(json.loads(out.read_text())['type'],'dsp_discovery_error')
