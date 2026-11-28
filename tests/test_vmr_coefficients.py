import json
import tempfile
import unittest
from pathlib import Path
from test_core import synthetic_pe
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.vmr_coefficients import WEIGHTS, verify
from skell_vst_decompiler.research_index import records

ROOT=Path(__file__).resolve().parents[1]

class TestCoefficientProvenance(unittest.TestCase):
    def test_wrong_fingerprint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'FG-2A.epl';p.write_bytes(synthetic_pe())
            with self.assertRaisesRegex(ValueError,'fingerprint'):verify(PE(p))
    def test_complete_scoped_weight_links(self):
        report=json.loads((ROOT/'reports/vmr_fg2a_coefficient_provenance.json').read_text())
        self.assertEqual(report['weight_origins_verified'],9)
        self.assertEqual(report['weight_consumer_endpoints_verified'],9)
        self.assertEqual(report['weight_origins_total'],9)
        self.assertEqual({int(x['field'],16) for x in report['weight_links']},{x[0] for x in WEIGHTS})
        self.assertEqual(len({x['consumer_read_rva'] for x in report['weight_links']}),9)
        self.assertEqual(len({x['initializer_store_rva'] for x in report['weight_links']}),9)
        self.assertNotIn('weights',report)
    def test_index_and_scope(self):
        rows=records([ROOT/'reports/vmr_fg2a_coefficient_provenance.json'])
        self.assertEqual(len(rows),16)
        self.assertEqual(sum(x['region']['checkpoint_count'] for x in rows),173)
        self.assertIn('fg2a_rational_stage',{x['region']['id'] for x in rows})
        self.assertTrue(all('runtime' in x['region']['confidence'] for x in rows))
