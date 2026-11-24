import unittest
from skell_vst_decompiler.boundary_audit import audit_boundaries


class BoundaryAuditTest(unittest.TestCase):
    def test_exact_missing_interior_conflict(self):
        sha='a'*64
        wanted=[16,20,40,60,80]
        def doc(name,pairs):
            return {'engine':name,'binary_sha256':sha,'entries':[{'requested':a,'entry':b} for a,b in pairs]}
        a=doc('a',[(16,16),(20,16),(40,40),(60,56)])
        b=doc('b',[(16,16),(20,20),(40,40),(60,56)])
        result=audit_boundaries(sha,[(16,32,100)],[a,b],wanted)
        self.assertEqual([r['status'] for r in result['entries']],
            ['corroborated_entry','conflicting_entries','corroborated_entry','different_entry','unobserved'])
        self.assertEqual([r['unwind_status'] for r in result['entries']],
            ['exact_start','interior','missing','missing','missing'])
        self.assertEqual(result['review_count'],2)
        with self.assertRaises(ValueError):audit_boundaries('b'*64,[],[a],wanted)
        with self.assertRaises(ValueError):audit_boundaries(sha,[],[a,a],wanted)
        with self.assertRaises(ValueError):audit_boundaries(sha,[],[doc('a',[(16,16),(16,16)])],wanted)

if __name__=='__main__':unittest.main()
