import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.classgraph import class_graph, class_plan, compare_rizin
from skell_vst_decompiler.pe import PE, PEFormatError


@unittest.skipUnless(shutil.which('clang++') and shutil.which('lld-link'), 'requires clang++ and lld-link')
class TestCompiledClassGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        root = Path(cls.tmp.name)
        obj, exe = root/'fixture.obj', root/'fixture.exe'
        source = Path(__file__).resolve().parent/'fixtures'/'classgraph_fixture.cpp'
        subprocess.run(['clang++','--target=x86_64-pc-windows-msvc','-O1','-fno-exceptions','-fno-stack-protector','-c',str(source),'-o',str(obj)],check=True,timeout=30)
        subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/out:'+str(exe),str(obj)],check=True,timeout=30)
        cls.pe = PE(exe)

    def test_multiple_inheritance_and_plan(self):
        graph = class_graph(self.pe,'Filter')
        self.assertEqual(len(graph['classes']),1)
        c = graph['classes'][0]
        tables = c['vtables']
        self.assertEqual(sorted(t['subobject_offset'] for t in tables),[0,8])
        self.assertEqual([b['type'] for b in tables[0]['hierarchy']['base_records']],['.?AUFilter@@','.?AUBase@@','.?AUSide@@'])
        table = tables[0]
        plan = class_plan(self.pe,'Filter',c['type'],int(table['vtable_rva'],16),[0])
        self.assertEqual(plan['targets'][0]['requested_rva'],table['candidate_slots'][0]['rva'])
        with self.assertRaises(ValueError):class_plan(self.pe,'Filter',c['type'],int(table['vtable_rva'],16),[63])

    def test_corrupt_locator_does_not_match(self):
        graph=class_graph(self.pe,'Filter'); c=graph['classes'][0]
        section=self.pe.section('.rdata'); raw=bytearray(self.pe.data)
        for t in c['vtables']:
            loc=section.file_offset+int(t['locator_rva'],16)-section.rva
            struct.pack_into('<I',raw,loc+20,0)
        path=Path(self.tmp.name)/'bad.exe';path.write_bytes(raw)
        self.assertFalse(class_graph(PE(path),'Filter')['classes'])

    def test_analyzer_reconciliation_rebase_dedup(self):
        t=class_graph(self.pe,'Filter')['classes'][0]['vtables'][0]
        rva=int(t['candidate_slots'][0]['rva'],16);base=0x140000000
        doc={'binary_sha256':self.pe.sha256,'image_base':base,'functions':[{'offset':base+rva},{'offset':base+rva},{'offset':base+1}]}
        result=compare_rizin(self.pe,doc)
        self.assertEqual(sum(result['counts'].values()),2)
        self.assertEqual(result['counts']['not_file_backed_executable'],1)
        self.assertEqual(result['functions'][0]['rva'],hex(rva))
        with self.assertRaises(ValueError):compare_rizin(self.pe,{**doc,'binary_sha256':'bad'})
        with self.assertRaises(ValueError):compare_rizin(self.pe,{**doc,'functions':[{'offset':True}]})
