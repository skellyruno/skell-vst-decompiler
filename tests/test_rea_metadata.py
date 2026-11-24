import json
import unittest
from skell_vst_decompiler.rea_metadata import normalize


class ReaMetadataTests(unittest.TestCase):
    def fixture(self):
        sha='a'*64
        return {'operation':'inspect_pe_imports','evidence_id':'ev_'+'b'*64,
                'subject':{'identity':{'sha256':sha}},'normalized_result':{
                'artifact':{'sha256':sha,'bytes':1024,'path':'private'},
                'machine':332,'bits':32,'format':'pe32',
                'coverage':{'status':'complete','imports':1,'delay_imports':0,'examined_dlls':1},
                'imports':[{'name':'Owned.dll','functions':[{'name':'probe','ordinal':None,'iat_rva':4096}]}],
                'delay_imports':[],'issues':[],'imphash':{'md5':'c'*32}}}

    def parse(self,x):return normalize(json.dumps(x).encode(),'a'*64,1024)

    def test_complete(self):
        r=self.parse(self.fixture())
        self.assertEqual(r['rows'],[('imports','owned.dll','probe',None,4096)])
        self.assertNotIn('private',json.dumps(r))

    def test_reject_scope_and_partial(self):
        for field,value in [('operation','other'),('subject',{'identity':{'sha256':'d'*64}})]:
            x=self.fixture();x[field]=value
            with self.assertRaises(ValueError):self.parse(x)
        x=self.fixture();x['normalized_result']['coverage']['status']='partial'
        with self.assertRaises(ValueError):self.parse(x)

    def test_reject_inconsistent_import(self):
        x=self.fixture();x['normalized_result']['imports'][0]['functions'][0]['ordinal']=1
        with self.assertRaises(ValueError):self.parse(x)
        x=self.fixture();x['normalized_result']['coverage']['imports']=2
        with self.assertRaises(ValueError):self.parse(x)

if __name__=='__main__':unittest.main()
