"""Fingerprint-bound native DSP path verification, never execute supplied plugins.

Stores bounded code hashes, selected instruction identities, direct calls,
scalar clues, and hashed dispatch-table topology (not vendor tables or code).
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from .pe import PE
from .disasm import disassemble, direct_calls

MAX_REPORT = 2_000_000


def verify(pe, report, objdump='objdump'):
    if report.get('schema_version') != 1 or report.get('type') != 'verified_static_signal_paths':
        raise ValueError('Unexpected manifest schema')
    matched = [row for row in report['regions'] if row['file'] == pe.path.name]
    if not 1 <= len(matched) <= 64 or any(row['binary_sha256'] != pe.sha256 for row in matched):
        raise ValueError('No exact matching source fingerprint')
    instructions = {}
    count = 0
    for row in matched:
        start, stop = int(row['start'], 16), int(row['end'], 16)
        if not 0 < stop-start <= 32768:
            raise ValueError('Invalid region boundaries')
        raw = pe.at_rva(start, stop-start, executable=True)
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Code region hash mismatch')
        decoded = disassemble(pe, start, stop-start, objdump)
        current = {i.address-pe.image_base: i for i in decoded}
        checks = row['checks']
        if not 1 <= len(checks) <= 4096 or len({a for a,_ in checks}) != len(checks):
            raise ValueError('Invalid checkpoint set')
        for addr, opcode in checks:
            rva = int(addr, 16)
            if not start <= rva < stop or rva not in current or current[rva].mnemonic != opcode:
                raise ValueError('Native mnemonic mismatch')
            count += 1
        instructions.update(current)
    calls = {int(x['site'],16):int(x['target'],16) for x in report.get('calls', []) if x['file']==pe.path.name}
    if len(calls)>4096:
        raise ValueError('Too many direct-call assertions')
    for site, target in calls.items():
        i=instructions.get(site)
        if (i is None or i.mnemonic != 'call' or not re.fullmatch(r'0x[0-9a-f]+(?:\s+<[^<>\r\n]{1,256}>)?', i.operands)
                or i.operands.split(' ',1)[0] != hex(pe.image_base+target)):
            raise ValueError('Native call target mismatch')
        pe.at_rva(target,1,executable=True)
    constants=0
    for entry in report.get('constants',[]):
        if entry['file'] != pe.path.name:continue
        pos=int(entry['rva'],16)
        expected=struct.pack('<f',float(entry['f32']))
        if pe.at_rva(pos,4)!=expected:
            raise ValueError('Native scalar mismatch')
        constants+=1
    tables=0
    for row in report.get('vcc_tables',[]):
        if row['file']!=pe.path.name:continue
        if row['binary_sha256']!=pe.sha256 or not 1<=row['entries']<=64:
            raise ValueError('Invalid table identity or size')
        if row['entries']%3 or row['triplets']!=row['entries']//3:
            raise ValueError('Invalid stage-triplet count')
        raw=pe.at_rva(int(row['rva'],16),8*row['entries'])
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('Dispatch table hash mismatch')
        pointers=[ptr-pe.image_base for (ptr,) in struct.iter_unpack('<Q',raw)]
        if len(set(pointers))!=row['unique_targets']:
            raise ValueError('Dispatch target cardinality mismatch')
        for ptr in pointers:pe.at_rva(ptr,1,executable=True)
        tables+=1
    return {'sha256':pe.sha256,'regions':len(matched),'checkpoints':count,
            'direct_calls':len(calls),'scalar_constants':constants,'dispatch_tables':tables}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--objdump',choices=['objdump','llvm-objdump'],default='objdump')
    args=parser.parse_args()
    if args.report.is_symlink() or not args.report.is_file() or args.report.stat().st_size>MAX_REPORT:
        raise ValueError('Unexpected evidence manifest path or size')
    print(json.dumps(verify(PE(args.binary),json.loads(args.report.read_text()),args.objdump),sort_keys=True))


if __name__=='__main__':main()
