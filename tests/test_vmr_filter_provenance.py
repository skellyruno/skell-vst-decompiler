import json
import tempfile
import unittest
from pathlib import Path
from test_core import synthetic_pe
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.vmr_filter_provenance import ACTIVE, BANKS, verify
from skell_vst_decompiler.research_index import records

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT/'reports/vmr_fg2a_filter_provenance.json'

class TestFilterProvenance(unittest.TestCase):
    def test_wrong_fingerprint_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'FG-2A.epl';p.write_bytes(synthetic_pe())
            with self.assertRaisesRegex(ValueError,'fingerprint'):verify(PE(p))

    def test_six_banks_and_distinct_stereo_states(self):
        data=json.loads(REPORT.read_text())
        self.assertEqual(data['filter_records_linked'],len(BANKS))
        self.assertEqual(data['active_coefficient_fields_linked'],30)
        self.assertEqual(data['channel_read_endpoints_verified'],60)
        self.assertEqual({int(b['record_offset'],16) for b in data['filter_links']},{b[0] for b in BANKS})
        all_states=[];all_sites=[]
        for b in data['filter_links']:
            self.assertEqual(len(b['copy_store_rvas']),3)
            self.assertEqual([c['channel'] for c in b['channels']],[0,1])
            for c in b['channels']:
                self.assertEqual(set(c['read_sites']),{role for role,_ in ACTIVE})
                all_states.extend(c['state_offsets']);all_sites.extend(c['read_sites'].values())
        self.assertEqual(len(set(all_states)),24)
        self.assertEqual(len(set(all_sites)),60)

    def test_feedback_writers_and_search(self):
        data=json.loads(REPORT.read_text())
        self.assertEqual(data['feedback_curve_write_endpoints_verified'],17)
        self.assertEqual({int(x['field'],16) for x in data['feedback_curve_write_sites']},set(range(0x160,0x1e8,8)))
        rows=records([REPORT]);self.assertEqual(len(rows),len(data['regions']))
        self.assertEqual(sum(x['region']['checkpoint_count'] for x in rows),data['checkpoint_count'])
        self.assertIn('fg2a_feedback_nonlinearity',{x['region']['id'] for x in rows})
        self.assertNotIn('coefficient_values',data)
        self.assertIn('runtime/audio remain unverified',data['limits'])

if __name__=='__main__':unittest.main()
