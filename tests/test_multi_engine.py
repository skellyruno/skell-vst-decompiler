import unittest
from skell_vst_decompiler.multi_engine import reconcile_observations


class MultiEngineTest(unittest.TestCase):
    def test_separate_evidence_types(self):
        sha='a'*64
        entry={'kind':'function_entry','subject':16,'value':16}
        edge={'kind':'function_call','subject':16,'value':32}
        other={'kind':'function_call','subject':16,'value':48}
        def doc(name,rows):
            return {'engine':name,'binary_sha256':sha,'observations':rows}
        result=reconcile_observations(sha,[doc('a',[entry,edge,other]),doc('b',[entry]),doc('c',[edge])])
        self.assertEqual(len(result['claims']),3)
        self.assertEqual([r['status'] for r in result['claims']],['corroborated_static','single_observation','corroborated_static'])
        with self.assertRaises(ValueError):
            reconcile_observations(sha,[doc('a',[entry]),doc('a',[edge])])
        with self.assertRaises(ValueError):
            reconcile_observations('b'*64,[doc('a',[entry])])
        with self.assertRaises(ValueError):
            reconcile_observations(sha,[doc('a',[entry,entry])])


if __name__=='__main__': unittest.main()
