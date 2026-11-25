import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from skell_vst_decompiler.architecture_intake import architecture, state_corpus
from skell_vst_decompiler.ghidra_bridge import command


class ArchitectureIntakeTests(unittest.TestCase):
    def test_distinguish_static_and_literal(self):
        parent = Mock(path=Path('/private/wrapper.dll'), sha256='parent', image_base=0x400000,
                      data=b'engine.dll\0' + 'other.dll\0'.encode('utf-16le'))
        parent.imports.return_value = {1: {'dll': 'Engine.DLL', 'symbol': 'CreateEngine'},
                                         2: {'dll': 'kernel32.dll', 'symbol': 'GetProcAddress'}}
        child = Mock(sha256='child', image_base=0x180000000)
        with patch('skell_vst_decompiler.architecture_intake.bounded_pe', side_effect=[parent, child, child, child]):
            result = architecture(parent.path, ['/private/engine.dll', '/private/other.dll', '/private/absent.dll'])
        self.assertEqual([x['status'] for x in result['adjacent_candidates']], ['STATIC_IMPORT', 'LITERAL_ONLY', 'NO_EDGE_OBSERVED'])
        self.assertEqual(result['loader_api_imports'], ['GetProcAddress'])

    def test_reject_nonadjacent(self):
        parent = Mock(path=Path('/private/wrapper.dll'), data=b'', sha256='p')
        parent.imports.return_value = {}
        with patch('skell_vst_decompiler.architecture_intake.bounded_pe', return_value=parent):
            with self.assertRaises(ValueError):
                architecture(parent.path, ['/elsewhere/engine.dll'])
            with self.assertRaises(ValueError):
                architecture(parent.path, ['/private/A.dll', '/private/a.dll'])

    def test_corpus_opaque_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name, raw in [('a', b'\0'*124), ('b', b'\0'*124), ('c', b'\1'+b'\0'*123), ('bad', b'x')]:
                (p/name).write_bytes(raw)
            r = state_corpus(sorted(p.iterdir()), 124, [{'offset': 0, 'length': 4, 'kind': 'mapped'}, {'offset': 4, 'length': 120, 'kind': 'opaque'}])
            self.assertEqual((r['matching_size'], r['unique_matching_contents'], r['rejected_size_or_file']), (3, 2, 1))
            self.assertEqual((r['declared_mapped_bytes'], r['declared_opaque_bytes'], r['unclassified_bytes']), (4, 120, 0))
            self.assertEqual(r['varying_offsets'], [0])
            with self.assertRaises(ValueError):
                state_corpus([p/'a'], 124, [{'offset': 0, 'length': 4}, {'offset': 3, 'length': 2}])

    def test_retention_is_opt_in(self):
        plan = {'binary_sha256': 'a'*64, 'targets': [{'requested_rva': '0x1000'}]}
        self.assertIn('-deleteProject', command('analyzer', 'project', 'binary', 'output', plan))
        self.assertNotIn('-deleteProject', command('analyzer', 'project', 'binary', 'output', plan, retain_project=True))
        self.assertNotIn('-overwrite', command('analyzer', 'project', 'binary', 'output', plan, retain_project=True))
