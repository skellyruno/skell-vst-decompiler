import unittest
from pathlib import Path
from skell_vst_decompiler.track_audit import compare_ranges,audit_tracks


class TrackAuditTests(unittest.TestCase):
    def test_exact_scope_and_conflicts(self):
        a,b='a'*64,'b'*64
        def row(name,sha,start,end,digest):
            return {'report':name,'binary_sha256':sha,'region':{'id':'r','start_rva':hex(start),
                    'end_rva_exclusive':hex(end),'sha256':digest}}
        rows=[row('one',a,16,32,a),row('two',a,16,32,b),row('three',b,16,32,b),
              row('four',a,16,33,b),row('five',a,20,24,None)]
        x=compare_ranges(rows,{a,b})
        self.assertEqual(x['region_records'],5)
        self.assertEqual(x['distinct_ranges'],4)
        self.assertEqual(x['records_without_region_digest'],1)
        self.assertEqual(len(x['candidate_digest_conflicts']),1)
        self.assertEqual(x['candidate_digest_conflicts'][0]['binary_sha256'],a)
        with self.assertRaises(ValueError):compare_ranges([rows[0],rows[0]],{a})

    def test_archived_tracks(self):
        root=Path(__file__).resolve().parents[1]/'reports'
        x=audit_tracks(root)['tracks']
        for name,count,hashed in [('TVB',64,29),('VMR',64,64),('Evo',0,0)]:
            self.assertEqual(x[name]['region_records'],count)
            self.assertEqual(x[name]['records_with_region_digest'],hashed)
            self.assertEqual(x[name]['distinct_ranges'],count)
            self.assertEqual(x[name]['candidate_digest_conflicts'],[])
        self.assertTrue(x['Evo']['metadata_only'])


if __name__=='__main__':unittest.main()
