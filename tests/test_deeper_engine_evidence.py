"""Checked evidence-index structure; no proprietary binaries in public CI."""
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class DeeperEngineEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads((ROOT/'reports/native_scoped/deeper_engines_2026_11_25.json').read_text())

    def test_unique_bounded_regions_and_cross_decoder_sample_count(self):
        rows=self.report
        self.assertEqual(len(rows),7)
        self.assertEqual(sum(len(row['checks']) for row in rows),141)
        self.assertEqual(len({row['id'] for row in rows}),len(rows))
        self.assertEqual(len({row['binary_sha256'] for row in rows}),5)
        for r in rows:
            self.assertRegex(r['sha256'],r'^[0-9a-f]{64}$')
            self.assertRegex(r['binary_sha256'],r'^[0-9a-f]{64}$')
            start,end=int(r['start'],16),int(r['end'],16)
            self.assertGreater(end,start)
            self.assertLessEqual(end-start,32768)
            seen=set()
            for a,mnemonic in r['checks']:
                pos=int(a,16)
                self.assertGreaterEqual(pos,start)
                self.assertLess(pos,end)
                self.assertNotIn(pos,seen)
                seen.add(pos)
                self.assertRegex(mnemonic,r'^[a-z][a-z0-9]*$')

    def test_biquad_input_output_carry_endpoints(self):
        row=next(r for r in self.report if r['id']=='gem_five_term_iir_and_state')
        check={a:m for a,m in row['checks']}
        for a in ('0x5605ee','0x5605f4','0x5605fb','0x560602'):
            self.assertEqual(check[a],'mov')
        self.assertEqual(check['0x560605'],'ret')
        self.assertEqual(check['0x560159'],'mulss')
        self.assertEqual(check['0x560191'],'mulss')

    def test_other_engine_evidence_anchors(self):
        rows={r['id']:r for r in self.report}
        self.assertEqual({k for k in rows if k.startswith('gem_')},
            {'gem_five_term_iir_and_state','gem_four_nonlinear_passes','gem_nonlinear_envelope_32'})
        self.assertIn(['0x24700b','and'],rows['aireq_64tap_circular_fir']['checks'])
        self.assertIn(['0x145460','call'],rows['aireqearth_mode_dispatch']['checks'])
        self.assertIn(['0x15e09e','mulsd'],rows['fg401_directional_double_smoother']['checks'])
        self.assertIn(['0x176a88','mulsd'],rows['vcc_parameter_ramp_not_color_core']['checks'])

if __name__=='__main__':unittest.main()
