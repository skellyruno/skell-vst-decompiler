import json
import os
from pathlib import Path
import tempfile
import unittest
from skell_vst_decompiler.analysis_cache import encode,sha
from skell_vst_decompiler.cache_policy import prune_cache, stable_stat
from skell_vst_decompiler.dependency_identity import parse_ldd
from skell_vst_decompiler.engine_batch import run_batch


class CachePolicyTest(unittest.TestCase):
    def test_verified_entries_only_and_budget(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            def write(i):
                identity={'schema':1,'binary':'a'*64,'scope':[i,8],'engine':{},'code':{},'python':[3,11,0],'environment':'fixture'}
                observation={'calls':{}}
                path=root/(sha(encode(identity))+'.json')
                path.write_bytes(encode({'identity':identity,'observation':observation,'digest':sha(encode(observation))}))
                os.utime(path,ns=(i+1,i+1))
                return path
            paths=[write(i) for i in range(3)]
            other=root/'research.json'; other.write_text('{}')
            invalid=root/('b'*64+'.json'); invalid.write_text('{}')
            link=root/('c'*64+'.json')
            try: link.symlink_to(paths[-1])
            except OSError: link=None
            result=prune_cache(root,max_entries=1,max_bytes=100000)
            self.assertEqual(result['removed'],2)
            self.assertTrue(result['within_limits'])
            self.assertFalse(paths[0].exists())
            self.assertFalse(paths[1].exists())
            self.assertTrue(paths[2].exists())
            self.assertTrue(other.exists() and invalid.exists())
            if link is not None:self.assertTrue(link.is_symlink())
            result=prune_cache(root,max_entries=100,max_bytes=0)
            self.assertEqual(result['remaining_entries'],0)
            self.assertTrue(other.exists() and invalid.exists())

    def test_access_time_not_content_mutation(self):
        from types import SimpleNamespace
        info=dict(st_dev=1,st_ino=2,st_mode=0o100600,st_size=3,st_mtime_ns=4,st_ctime_ns=5)
        self.assertEqual(stable_stat(SimpleNamespace(**info,st_atime_ns=1)),
                         stable_stat(SimpleNamespace(**info,st_atime_ns=2)))
        self.assertNotEqual(stable_stat(SimpleNamespace(**info)),
                            stable_stat(SimpleNamespace(**{**info,'st_size':4})))

    def test_invalid_budget_before_target(self):
        with self.assertRaises(ValueError): run_batch('missing',[(1,2)],cache_limits=(1,1))
        with self.assertRaises(ValueError): run_batch('missing',[(1,2)],cache_dir='tmp',environment_id='x',cache_limits=(-1,1))

    def test_dependency_parser(self):
        rows='linux-vdso.so.1 (0x123)\nlibc.so.6 => /lib/libc.so.6 (0x456)\n/lib/ld-linux.so (0x789)\n'
        self.assertEqual(parse_ldd(rows),sorted({str(Path('/lib/libc.so.6').resolve()),str(Path('/lib/ld-linux.so').resolve())}))
        with self.assertRaises(RuntimeError): parse_ldd('libfoo.so => not found')
        with self.assertRaises(RuntimeError): parse_ldd('unexpected output')


if __name__=='__main__': unittest.main()
