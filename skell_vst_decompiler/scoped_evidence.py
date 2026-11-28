"""Verify bounded, exact-build evidence manifests without executing targets."""
import argparse
import hashlib
import json
from pathlib import Path
from .pe import PE
from .disasm import disassemble


def verify(pe, rows, objdump='objdump'):
    selected = [r for r in rows if r['file'] == pe.path.name]
    if not 1 <= len(selected) <= 128:
        raise ValueError('No matching bounded source manifest')
    if any(r['binary_sha256'] != pe.sha256 for r in selected):
        raise ValueError('Unexpected source fingerprint')
    count = 0
    for r in selected:
        start, end = int(r['start'], 16), int(r['end'], 16)
        if not 0 < end-start <= 32768:
            raise ValueError('Invalid bounded region')
        if hashlib.sha256(pe.at_rva(start, end-start, executable=True)).hexdigest() != r['sha256']:
            raise ValueError('Region hash mismatch')
        checks = r['checks']
        if not 1 <= len(checks) <= 4096 or len({a for a, _ in checks}) != len(checks):
            raise ValueError('Invalid checkpoints')
        by = {i.address-pe.image_base: i.mnemonic for i in disassemble(pe, start, end-start, objdump)}
        for a, mnemonic in checks:
            address = int(a, 16)
            if not start <= address < end or by.get(address) != mnemonic:
                raise ValueError('Instruction checkpoint mismatch')
            count += 1
    return {'binary_sha256': pe.sha256, 'regions': len(selected), 'checks': count}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary', type=Path)
    p.add_argument('--report', required=True, type=Path)
    a = p.parse_args()
    if a.report.stat().st_size > 2_000_000:
        raise ValueError('Manifest too large')
    print(json.dumps(verify(PE(a.binary), json.loads(a.report.read_text())), sort_keys=True))
