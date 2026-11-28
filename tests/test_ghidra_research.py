import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_core import synthetic_pe
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.ghidra_bridge import make_plan, validate_output, run_analysis, command, launcher
from skell_vst_decompiler.research_index import records, query, target_rvas


class TestGhidraResearch(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.binary=self.root/'local sample.vst3';self.binary.write_bytes(synthetic_pe())
        self.pe=PE(self.binary)
        self.plan=make_plan(self.pe,[0x1000,0x1001])
        self.output=self.root/'output';self.output.mkdir()

    def output_files(self, rows=None, edges=None):
        (self.output/'results.tsv').write_text('SKELL_SHA256\t'+self.pe.sha256+'\n'+(rows if rows is not None else '0x1000\t0x1000\tok\tfunction_1000.c.txt\n0x1001\t0x1000\tok\tfunction_1000.c.txt\n')+'SKELL_COMPLETE\n')
        (self.output/'calls.tsv').write_text((edges if edges is not None else '0x1000\tcalls\t0x1003\n')+'SKELL_COMPLETE\n')
        (self.output/'function_1000.c.txt').write_text('int fixture(void) { return 1; }\n')

    def test_plan_is_fingerprint_bound_and_bounded(self):
        self.assertEqual(len(make_plan(self.pe,[0x1000,0x1000])['targets']),1)
        with self.assertRaises(ValueError):make_plan(self.pe,[])
        with self.assertRaises(ValueError):make_plan(self.pe,list(range(0x1000,0x1041)))
        with self.assertRaises(PEFormatError):make_plan(self.pe,[0x3000])
        with self.assertRaises(ValueError):make_plan(self.pe,[],[{'schema_version':1,'binary_sha256':'0'*64,'regions':[]}])

    def test_manifest_duplicate_functions_and_call_links(self):
        self.output_files()
        r=validate_output(self.output,self.plan)
        self.assertEqual(r['decompiled_target_count'],2)
        self.assertEqual(r['unique_decompiled_function_count'],1)
        self.assertEqual(r['status'],'complete')
        self.assertEqual(r['call_links'][0]['related_rva'],'0x1003')
        self.assertEqual(len(set(x['local_pseudocode'] for x in r['targets'])),1)

    def test_reject_partial_manifest_path_traversal_and_extra_edges(self):
        self.output_files(rows='0x1000\t0x1000\tok\t../x\n0x1001\t-\tno_function\t-\n')
        with self.assertRaises(RuntimeError):validate_output(self.output,self.plan)
        self.output_files(rows='0x1000\t0x1000\tok\tfunction_1000.c.txt\n')
        with self.assertRaises(RuntimeError):validate_output(self.output,self.plan)
        self.output_files(edges='0x1000\tcalls\t0x1003\n0x1000\tcalls\t0x1003\n')
        with self.assertRaises(RuntimeError):validate_output(self.output,self.plan)
        self.output_files(edges='0x1002\tcalls\t0x1003\n')
        with self.assertRaises(RuntimeError):validate_output(self.output,self.plan)
        self.output_files();(self.output/'calls.tsv').write_text('incomplete')
        with self.assertRaises(RuntimeError):validate_output(self.output,self.plan)

    def test_explicit_failed_target(self):
        self.output_files(rows='0x1000\t0x1000\tok\tfunction_1000.c.txt\n0x1001\t-\tno_function\t-\n')
        r=validate_output(self.output,self.plan)
        self.assertEqual(r['status'],'partial');self.assertEqual(r['decompiled_target_count'],1)

    def test_argv_and_missing_launcher(self):
        with self.assertRaises(FileNotFoundError):launcher(self.root)
        args=command(self.root/'fake',self.root/'project',self.binary,self.output,self.plan)
        self.assertIn(str(self.binary),args);self.assertIn('-deleteProject',args)
        self.assertNotIn('-overwrite',args)
        with self.assertRaises(ValueError):command('a','b','c','d',self.plan,0)

    @unittest.skipIf(os.name=='nt','POSIX mock executable fixture')
    def test_fake_analyzer_end_to_end_not_real_ghidra(self):
        home=self.root/'ghidra';(home/'support').mkdir(parents=True)
        fake=home/'support'/'analyzeHeadless'
        fake.write_text('''#!/usr/bin/env python3
import pathlib,sys
p=sys.argv.index('-postScript');out=pathlib.Path(sys.argv[p+2]);sha=sys.argv[p+3]
(out/'function_1000.c.txt').write_text('synthetic fixture only')
(out/'results.tsv').write_text('SKELL_SHA256\\t'+sha+'\\n0x1000\\t0x1000\\tok\\tfunction_1000.c.txt\\n0x1001\\t0x1000\\tok\\tfunction_1000.c.txt\\nSKELL_COMPLETE\\n')
(out/'calls.tsv').write_text('0x1000\\tcalls\\t0x1003\\nSKELL_COMPLETE\\n')
''');fake.chmod(0o700)
        work=self.root/'jobs';r=run_analysis(self.pe,self.plan,home,work,1)
        self.assertEqual(r['status'],'complete');self.assertEqual(self.pe.sha256,PE(self.binary).sha256)
        r2=run_analysis(self.pe,self.plan,home,work,1);self.assertNotEqual(r['job'],r2['job'])
        tampered=dict(self.plan);tampered['image_base']='0x0'
        with self.assertRaises(ValueError):run_analysis(self.pe,tampered,home,work,1)

    def test_index_aggregates_and_isolates_builds(self):
        region={'id':'gain','title':'Ducking gain','start_rva':'0x1000','end_rva_exclusive':'0x1004'}
        a={'schema_version':1,'source':'A','binary_sha256':self.pe.sha256,'regions':[region]}
        b={**a,'source':'B','binary_sha256':'f'*64}
        f=self.root/'report.json';f.write_text(json.dumps([a,b]))
        rows=records([f]);self.assertEqual(len(rows),2)
        self.assertEqual(len(query(rows,'ducking gain')),2)
        self.assertEqual(len(query(rows,'gain',self.pe.sha256,address=0x1001)),1)
        self.assertFalse(query(rows,address=0x1004))
        self.assertEqual(target_rvas(rows,self.pe.sha256),[0x1000])
        b['regions']=[{**region,'end_rva_exclusive':'0x1000'}];f.write_text(json.dumps([a,b]))
        with self.assertRaises(ValueError):records([f])

if __name__=='__main__':unittest.main()
