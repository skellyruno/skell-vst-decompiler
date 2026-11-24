import json
import tempfile
import unittest
from pathlib import Path
from test_core import synthetic_pe
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.vmr_control import verify
from skell_vst_decompiler.research_index import records, query
from ghidra_smoke import fixture_exports

class TestVMRControlEvidence(unittest.TestCase):
    def test_wrong_fingerprint(self):
        with tempfile.TemporaryDirectory() as t:
            for name in ('FG-116.epl','FG-Stress.epl','FG-2A.epl'):
                path=Path(t)/name;path.write_bytes(synthetic_pe())
                with self.assertRaises(ValueError):verify(PE(path))
    def test_report_search_and_scope(self):
        path=Path(__file__).resolve().parents[1]/'reports'/'vmr_control_streams.json'
        rows=records([path]);self.assertEqual(len(rows),12)
        self.assertEqual(len(query(rows,'minimum-constrained')),1)
        self.assertEqual(len(query(rows,'coupled bounded')),1)
        self.assertEqual(sum(x['region']['checkpoint_count'] for x in rows),92)
    def test_no_fixture_exports(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'fixture.exe';path.write_bytes(synthetic_pe())
            with self.assertRaises(RuntimeError):fixture_exports(path)
