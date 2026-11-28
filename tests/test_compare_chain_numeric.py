import pathlib
import tempfile
import unittest
import numpy as np
from compare_chain_numeric import compare

class NumericCompareTests(unittest.TestCase):
    def test_accept_small_and_reject_material(self):
        with tempfile.TemporaryDirectory() as d:
            p,q=pathlib.Path(d)/'a',pathlib.Path(d)/'b'
            a=np.zeros(400,dtype='<f4');a.tofile(p)
            a[0]=1e-8;a.tofile(q);peak,rms=compare(p,q);self.assertLess(peak,2e-7)
            a[0]=1e-4;a.tofile(q)
            with self.assertRaises(AssertionError):compare(p,q)
            a[0]=np.nan;a.tofile(q)
            with self.assertRaises(ValueError):compare(p,q)
            a[:-1].tofile(q)
            with self.assertRaises(ValueError):compare(p,q)
