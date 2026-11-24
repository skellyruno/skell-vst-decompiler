import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch
from skell_vst_decompiler.rack_paths import pointer_slots, verify_tvb_rack, verify_vmr_paths
from skell_vst_decompiler.pe import PEFormatError
from skell_vst_decompiler.catalog import search

class Fixture:
    image_base=0x180000000
    path=Path('FG-116.epl')
    sha256='wrong'
    def at_rva(self,rva,n,executable=False):
        if executable and rva==0x1000 and n==1:return b'\xc3'
        if not executable and rva==0x2000 and n==16:return struct.pack('<QQ',self.image_base+0x1000,0)
        raise PEFormatError('not backed')

class RackPathTests(unittest.TestCase):
    def test_bounded_slots(self):
        self.assertEqual(pointer_slots(Fixture(),0x2000,2),[{'slot':0,'target_rva':'0x1000','executable_file_backed':True},{'slot':1,'target_rva':None,'executable_file_backed':False}])
    def test_invalid_ranges(self):
        for address,count in [(0x2001,2),(0x2000,0),(0x2000,65)]:
            with self.assertRaises(ValueError):pointer_slots(Fixture(),address,count)
        with self.assertRaises(PEFormatError):pointer_slots(Fixture(),0x3000,2)
    def test_source_identity(self):
        with patch('skell_vst_decompiler.rack_paths.disassemble') as d:
            for fn in (verify_tvb_rack,verify_vmr_paths):
                with self.assertRaises(ValueError):fn(Fixture())
            d.assert_not_called()
    def test_catalog(self):
        p=Path(__file__).resolve().parents[1]/'reports/tvb_rack_paths.json'
        report=json.loads(p.read_text())
        self.assertEqual(search(report,'0x5a5ef0')['matches'][0]['id'],'eq_coefficients')
        self.assertEqual(len(search(report,'limiter')['matches']),3)
        self.assertEqual(report['checkpoint_count'],sum(x['checkpoint_count'] for x in report['regions']))
