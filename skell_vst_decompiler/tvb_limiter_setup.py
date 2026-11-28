"""Recheck the bounded limiter evidence manifest without executing the PE."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from .disasm import disassemble, imported_call_sites
from .equations import TVB_SHA256
from .pe import PE


def verify(pe, report, objdump='objdump'):
    if pe.sha256 != TVB_SHA256 or report['binary_sha256'] != TVB_SHA256:
        raise ValueError('Unexpected source fingerprint')
    if report['schema_version'] != 1 or not 1 <= len(report['regions']) <= 16:
        raise ValueError('Unsupported manifest')
    count = calls = 0
    for region in report['regions']:
        start, end = (int(region[key], 16) for key in ('start_rva', 'end_rva_exclusive'))
        if not 0 < end-start <= 32768:
            raise ValueError('Invalid evidence range')
        if hashlib.sha256(pe.at_rva(start, end-start, executable=True)).hexdigest() != region['sha256']:
            raise ValueError('Code region hash mismatch')
        ins = disassemble(pe, start, end-start, objdump)
        by = {i.address-pe.image_base: i.mnemonic for i in ins}
        imports = {int(c['site_rva'], 16): c['symbol'] for c in imported_call_sites(pe, ins)}
        for address, mnemonic in region['checkpoints']:
            rva = int(address, 16)
            if not start <= rva < end or by.get(rva) != mnemonic:
                raise ValueError('Mnemonic checkpoint mismatch')
            count += 1
        for address, symbol in region['imports']:
            rva = int(address, 16)
            if not start <= rva < end or imports.get(rva) != symbol:
                raise ValueError('Import checkpoint mismatch')
            calls += 1
    for address, fmt, expected in report['constants']:
        if fmt not in ('f', 'd') or not math.isfinite(expected):
            raise ValueError('Invalid scalar format or value')
        actual = struct.unpack('<'+fmt, pe.at_rva(int(address, 16), struct.calcsize(fmt)))[0]
        if not math.isclose(actual, expected, rel_tol=1e-7, abs_tol=1e-15):
            raise ValueError('Scalar constant mismatch')
    if count != report['checkpoint_count'] or calls != report['import_count']:
        raise ValueError('Evidence count mismatch')
    return {'binary_sha256': pe.sha256, 'regions': len(report['regions']),
            'checkpoints': count, 'imports': calls, 'constants': len(report['constants'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary')
    parser.add_argument('--report', type=Path, default=Path('reports/limiter_setup/tvb_limiter_setup.json'))
    parser.add_argument('--objdump', default='objdump')
    args = parser.parse_args()
    print(json.dumps(verify(PE(args.binary), json.loads(args.report.read_text()), args.objdump), sort_keys=True))
