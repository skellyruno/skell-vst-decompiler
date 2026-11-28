import json
import unittest
from skell_vst_decompiler.craft_metadata import normalize


class CraftMetadataTest(unittest.TestCase):
    def record(self):
        return {'id':'ev_'+'a'*64,'subject':{'sha256':'b'*64,'name':'private path'},
                'operation':'native_layout_show','environment':{'engine':'builtin'},
                'coverage':{'status':'complete'},'result':{'bits':32,'format':'pe','image_base':'0x10000000',
                'sections':[{'name':'private symbol'}],'linkage':{'exports':1},'pseudocode':'discard'},
                'summary':'discard'}

    def parse(self,e):
        return normalize(json.dumps(e).encode(),'b'*64)

    def test_allowlist(self):
        result=self.parse(self.record())
        self.assertEqual(result['architecture'],'x86')
        self.assertEqual(result['section_count'],1)
        self.assertEqual(result['export_count'],1)
        self.assertNotIn('private',json.dumps(result))
        self.assertNotIn('discard',json.dumps(result))

    def test_reject_mismatched_source_and_scope(self):
        for key,value in [('subject',{'sha256':'c'*64}),('operation','native_function_pseudocode'),
                          ('environment',{'engine':'ghidra'}),('coverage',{'status':'partial'}),('id','fake')]:
            e=self.record();e[key]=value
            with self.assertRaises(ValueError):self.parse(e)

    def test_reject_invalid_counts(self):
        for key,value in [('bits',True),('image_base','0x100000000'),('sections',[]),('linkage',{'exports':-1})]:
            e=self.record();e['result'][key]=value
            with self.assertRaises(ValueError):self.parse(e)


if __name__=='__main__':unittest.main()
