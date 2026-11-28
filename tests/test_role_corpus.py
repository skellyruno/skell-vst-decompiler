import unittest
from skell_vst_decompiler.role_corpus import select_regions

class RoleCorpusTests(unittest.TestCase):
    def test_stratified_and_exact_anchor(self):
        rows=[(i,i+1,str(i)) for i in range(12)]
        freq={str(i):1 if i<6 else 31 for i in range(12)}
        a=select_regions(rows,freq,31)
        self.assertEqual([r[0] for r in a],[1,4,7,10])
        b=select_regions(rows,freq,31,[(1,2),(3,4)])
        self.assertEqual(len(b),5)
        self.assertEqual([r[0] for r in b if r[-1]=='prior_anchor'],[1,3])
        with self.assertRaises(ValueError):select_regions(rows,freq,31,[(100,101)])
