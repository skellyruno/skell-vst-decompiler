"""Bounded static SSE RIP-relative references; never reads vendor values."""
import hashlib
import re
from collections import Counter
from .disasm import disassemble
from .pe import PEFormatError

# Deliberately narrow legacy SSE forms with no trailing immediate.
OPS = {0x10:'mov', 0x11:'mov', 0x51:'sqrt', 0x58:'add', 0x59:'mul',
       0x5c:'sub', 0x5d:'min', 0x5e:'div', 0x5f:'max'}
SUFFIX = {0xf3:('ss',4), 0xf2:('sd',8), 0x66:('pd',16), 0:('ps',16)}


def decode_reference(raw, site):
    if not raw:
        return None
    i = 0
    prefix = raw[i] if raw[i] in (0x66,0xf2,0xf3) else 0
    i += bool(prefix)
    if i < len(raw) and 0x40 <= raw[i] <= 0x4f:
        i += 1
    if len(raw) != i+7 or raw[i] != 0x0f or raw[i+1] not in OPS:
        return None
    opcode, modrm = raw[i+1:i+3]
    if modrm & 0xc7 != 5:
        return None
    suffix,width = SUFFIX[prefix]
    return OPS[opcode]+suffix,width,site+len(raw)+int.from_bytes(raw[-4:],'little',signed=True),('write' if opcode==0x11 else 'read')


def audit_scope(pe, fingerprint, start, length):
    if pe.sha256 != fingerprint:
        raise PEFormatError('Binary fingerprint mismatch')
    if type(start) is not int or type(length) is not int or not 1 <= length <= 32768:
        raise ValueError('Invalid bounded scope')
    raw = pe.at_rva(start,length,executable=True)
    maps = [{x.address-pe.image_base:x for x in disassemble(pe,start,length,tool)
             if start <= x.address-pe.image_base < start+length} for tool in ('objdump','llvm-objdump')]
    nxt = [{a:b for a,b in zip(sorted(m),sorted(m)[1:])} for m in maps]
    rows, rejected = [], 0
    for site in sorted(maps[0].keys() | maps[1].keys()):
        a,b = (m.get(site) for m in maps)
        def candidate(x):
            return x is not None and x.mnemonic in {op+s for op in OPS.values() for s,_ in SUFFIX.values()} and '[rip' in x.operands.lower()
        if not (candidate(a) or candidate(b)):
            continue
        end = nxt[0].get(site)
        if end is None or end != nxt[1].get(site) or not candidate(a) or not candidate(b):
            rejected += 1
            continue
        v = decode_reference(raw[site-start:end-start],site)
        if v is None:
            rejected += 1
            continue
        op,width,target,access = v
        def agrees(x):
            match = re.search(r'#\s*0x([0-9a-fA-F]+)',x.operands)
            return x.mnemonic == op and match is not None and int(match[1],16)-pe.image_base == target
        if not agrees(a) or not agrees(b):
            rejected += 1
            continue
        sec = next((s for s in pe.sections if s.rva<=target and target+width<=s.rva+s.file_size),None)
        if sec is None or sec.executable:
            rejected += 1
            continue
        rows.append({'site':hex(site),'target':hex(target),'mnemonic':op,'width':width,'access':access,
                     'section':sec.name,'writable':bool(sec.characteristics & 0x80000000)})
    return {'start':hex(start),'bytes':length,'scope_sha256':hashlib.sha256(raw).hexdigest(),
            'references':rows,'rejected':rejected,'counts':dict(Counter((x['access']+'_'+('writable' if x['writable'] else 'readonly')) for x in rows)),
            'limits':'Selected legacy SSE RIP-relative operands only; no values, runtime routing, or DSP equation inference.'}
