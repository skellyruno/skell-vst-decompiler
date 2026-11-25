import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.scoped_evidence import verify


class ScopedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.pe = Mock(path=Path('fixture.dll'), sha256='owned', image_base=0x1000)
        self.pe.at_rva.return_value = b'\xc3'
        self.row = dict(file='fixture.dll', binary_sha256='owned', start='0x10', end='0x11', sha256=hashlib.sha256(b'\xc3').hexdigest(), checks=[['0x10', 'ret']])

    def test_valid_and_wrong_opcode(self):
        with patch('skell_vst_decompiler.scoped_evidence.disassemble', return_value=[Instruction(0x1010, 'ret', '')]):
            self.assertEqual(verify(self.pe, [self.row])['checks'], 1)
            self.row['checks'][0][1] = 'nop'
            with self.assertRaisesRegex(ValueError, 'Instruction checkpoint'):
                verify(self.pe, [self.row])

    def test_reject_wrong_source_before_read(self):
        self.pe.sha256 = 'different'
        with self.assertRaisesRegex(ValueError, 'source fingerprint'):
            verify(self.pe, [self.row])
        self.pe.at_rva.assert_not_called()

    def test_region_hash(self):
        self.pe.at_rva.return_value = b'\x90'
        with self.assertRaisesRegex(ValueError, 'Region hash'):
            verify(self.pe, [self.row])

    def test_manifest_counts(self):
        path = Path(__file__).resolve().parents[1]/'reports/native_scoped/gem_vmr_paths.json'
        rows = json.loads(path.read_text())
        self.assertEqual(len(rows), 11)
        self.assertEqual(len({r['binary_sha256'] for r in rows}), 4)
        self.assertEqual(sum(len(r['checks']) for r in rows), 113)
