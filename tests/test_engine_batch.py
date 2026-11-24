import unittest
from skell_vst_decompiler.engine_batch import agreement, run_batch


class BatchTests(unittest.TestCase):
    def test_three_engine_conflict_and_partial(self):
        scope = {'sha256':'a'*64,'start':16,'size':32}
        a=dict(scope,engine='a',calls={'0x10':'0x20','0x12':'0x24','0x14':'0x28'})
        b=dict(scope,engine='b',calls={'0x10':'0x20','0x12':'0x24','0x14':'0x28'})
        c=dict(scope,engine='c',calls={'0x10':'0x20','0x14':'0x30','0x18':'0x20'})
        self.assertEqual([r['status'] for r in agreement([a,b,c])],
                         ['agreed_static','partial_agreement','conflict','single_observation'])
        with self.assertRaises(ValueError): agreement([a,a])
        with self.assertRaises(ValueError): agreement([a,dict(c,size=64)])

    def test_limits_before_binary_read(self):
        with self.assertRaises(ValueError): run_batch('missing',[(16,32)],workers=3)
        with self.assertRaises(ValueError): run_batch('missing',[(16,32)],cache_dir='cache')
        with self.assertRaises(ValueError): run_batch('missing',[(16,32)]*2)


if __name__=='__main__': unittest.main()
