import struct
import tempfile
import unittest
from pathlib import Path
from test_legacy_pe import fixture
from skell_vst_decompiler.pe_export_audit import export_metadata


class ExportAuditTest(unittest.TestCase):
    def test_legacy_noncontiguous_tables(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'owned.dll';p.write_bytes(fixture())
            data=export_metadata(p)
            self.assertEqual(data['architecture'],'x86')
            self.assertEqual(data['public_entries'][0]['name'],'VSTPluginMain')
            self.assertEqual(data['public_entries'][0]['ordinal'],1)
            self.assertFalse(data['reccmp_contiguous_table_assumption'])

    def test_ordinal_outside_table(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'owned.dll';b=fixture()
            struct.pack_into('<H',b,584,2);p.write_bytes(b)
            with self.assertRaises(ValueError):export_metadata(p)

if __name__=='__main__':unittest.main()
