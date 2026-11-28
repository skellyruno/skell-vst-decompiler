import json
from pathlib import Path
import tempfile
import unittest
from skell_vst_decompiler.analysis_cache import reconcile_directory
from skell_vst_decompiler.engine_agreement import compare
from skell_vst_decompiler.research_index import records


class CacheTest(unittest.TestCase):
    def test_persistence_and_invalidation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            reports = root/'reports'; reports.mkdir()
            cache = root/'cache'
            snapshot = reports/'vmr_variant_navigation.json'
            snapshot.write_text(json.dumps({'schema_version':1,'binaries':[]}))
            first, hit = reconcile_directory(reports, cache)
            self.assertFalse(hit)
            self.assertEqual(reconcile_directory(reports, cache), (first, True))
            entry = next(cache.glob('*.json'))
            entry.write_text('{broken')
            self.assertEqual(reconcile_directory(reports, cache), (first, False))
            self.assertEqual(reconcile_directory(reports, cache), (first, True))
            snapshot.write_text(snapshot.read_text()+'\n')
            self.assertFalse(reconcile_directory(reports, cache)[1])
            dependency = reports/'metric.json'; dependency.write_text('{}')
            self.assertFalse(reconcile_directory(reports, cache)[1])
            dependency.write_text('{"changed":true}')
            self.assertFalse(reconcile_directory(reports, cache)[1])
            self.assertTrue(reconcile_directory(reports, cache)[1])
            dependency.unlink()
            # The exact previous input set may reuse its previous valid entry.
            self.assertTrue(reconcile_directory(reports, cache)[1])
            with self.assertRaises(ValueError):
                reconcile_directory(reports, reports/'cache')

    def test_benchmark_schema_is_not_evidence(self):
        path = Path(__file__).resolve().parents[1]/'reports'/'interval_index_benchmark_2026-11-24.json'
        self.assertEqual(records([path]), [])


class AgreementTest(unittest.TestCase):
    def test_conflict_single_and_agreement(self):
        scope = {'sha256':'a'*64,'start':16,'size':32}
        a = dict(scope,calls={16:32,20:36,24:40})
        b = dict(scope,calls={16:32,20:40,28:44})
        self.assertEqual([x['status'] for x in compare(a,b)],
                         ['agreed_static','conflict','single_observation','single_observation'])
        with self.assertRaises(ValueError):
            compare(a,dict(b,sha256='b'*64))
        with self.assertRaises(ValueError):
            compare(a,dict(b,size=64))


if __name__ == '__main__':
    unittest.main()
