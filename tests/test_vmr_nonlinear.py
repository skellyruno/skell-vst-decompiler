import json
import tempfile
import unittest
from pathlib import Path
from test_core import synthetic_pe
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.vmr_nonlinear import verify
from skell_vst_decompiler.evidence_book import build, markdown
from skell_vst_decompiler.research_index import records, query

ROOT=Path(__file__).resolve().parents[1]

class TestVMRNonlinear(unittest.TestCase):
    def test_reject_wrong_build(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('FG-116.epl','FG-2A.epl','FG-Stress.epl'):
                path=Path(d)/name;path.write_bytes(synthetic_pe())
                with self.assertRaises(ValueError):verify(PE(path))
    def test_verified_report_catalog(self):
        path=ROOT/'reports'/'vmr_nonlinear_paths.json'
        reports=json.loads(path.read_text());rows=records([path]);self.assertEqual(len(rows),16)
        self.assertEqual(sum(x['region']['checkpoint_count'] for x in rows),165)
        self.assertEqual({x['region']['id'] for x in query(rows,'even-power nonlinear')},{'fg2a_even_power_chain','fg2a_biquad_after_polynomial'})
        self.assertEqual(len(query(rows,'variable-coefficient state')),1)
        self.assertEqual(sum(len(t['slots']) for r in reports for t in r['dispatches']),17)
        self.assertTrue(all('runtime' in r['limits'] for r in reports))
    def test_atlas_is_deterministic(self):
        rows=records((ROOT/'reports').glob('*.json'));book=build(rows)
        self.assertEqual(book,build(list(reversed(rows))))
        self.assertEqual(book['region_count'],len(rows));self.assertIn('even-power',markdown(book))
        self.assertEqual(len(book['binaries']),4)
        self.assertEqual(markdown(book)+'\n',(ROOT/'docs'/'DSP_EQUATION_ATLAS.md').read_text())
    def test_calls_do_not_cross_source_fingerprint(self):
        def row(sha, key, start, end, calls):
            return {'source':'example','binary_sha256':sha,'report':'x.json','region':{'id':key,'title':key,'start_rva':hex(start),'end_rva_exclusive':hex(end),'equation':'unknown','direct_calls':calls}}
        rows=[row('a'*64,'a',16,32,[{'site_rva':'0x10','target_rva':'0x40'},{'site_rva':'0x0','target_rva':'0x40'}]),row('b'*64,'b',64,80,[]),row('a'*64,'c',64,80,[])]
        edges=build(rows)['binaries'][0]['entries'][0]['direct_calls']
        self.assertEqual(edges,[{'site_rva':'0x10','target_rva':'0x40','covering_evidence':['x.json::c']}])
