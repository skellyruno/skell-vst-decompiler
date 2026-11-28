import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from skell_vst_decompiler.rack_research_intake import ENDPOINTS, inventory, tvb_endpoints, module_dispatch


class IntakeTests(unittest.TestCase):
    def test_wrong_build(self):
        with patch('skell_vst_decompiler.rack_research_intake.disassemble') as decode:
            with self.assertRaises(ValueError):
                tvb_endpoints(Mock(sha256='wrong'))
            decode.assert_not_called()

    def test_endpoints(self):
        self.assertEqual(len(ENDPOINTS),17)
        by_name={row[0]:row for row in ENDPOINTS}
        self.assertEqual(len(by_name),17)
        self.assertEqual(by_name['delay_division'][4:],by_name['fx_delay_division'][4:])
        self.assertEqual(by_name['delay_duck'][4:],by_name['delay_duck_on'][4:])
        self.assertNotEqual(by_name['lim_true_peak'][4],by_name['lim_auto_release'][4])

    def test_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'test.epl').write_bytes(b'abc')
            (p/'ignore.dll').write_bytes(b'abc')
            self.assertEqual(inventory(p),[{'name':'test.epl','sha256':'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad','size':3}])

    def test_no_candidates(self):
        with patch('skell_vst_decompiler.rack_research_intake.class_graph',return_value={'classes':[]}):
            self.assertEqual(module_dispatch(Mock(sha256='fixture')),{'binary_sha256':'fixture','rows':[]})
