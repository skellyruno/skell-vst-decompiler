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
                scan.assert_called_once_with(binary,limit=32,tool='objdump')
                self.assertEqual(json.loads(out.read_text())['type'],'dsp_discovery')
                with self.assertRaises(ValueError):run_job(binary,out)
    def test_error_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'error.json'
            with patch('skell_vst_decompiler.dsp_job.shutil.which',return_value=None):
                self.assertEqual(run_job(root/'fixture.dll',out),1)
            self.assertEqual(json.loads(out.read_text())['type'],'dsp_discovery_error')
