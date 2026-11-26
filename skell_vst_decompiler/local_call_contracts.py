"""Conservative x64 static sample-call candidates, not runtime DSP identification."""
import hashlib
import re
from .disasm import disassemble
from .pe import PEFormatError


def canonical(ins):
    return ins.mnemonic.lower(), re.sub(r'\s+', '', ins.operands.split('#', 1)[0].lower())


def audit_scope(pe, fingerprint, start, length):
    """Find a narrow Windows x64 scalar in-place call contract in both decoders.

    No indirect target resolution: require a scaled sample load into xmm1,
    an object-table load into rax, call [rax+disp], and immediate result store
    to the same callee-saved base register. No inferred control flow.
    """
    if pe.sha256 != fingerprint:
        raise PEFormatError('Binary fingerprint mismatch')
    if type(start) is not int or type(length) is not int or not 1 <= length <= 32768:
        raise ValueError('Invalid bounded scope')
    raw = pe.at_rva(start, length, executable=True)
    streams = [[i for i in disassemble(pe,start,length,t) if start <= i.address-pe.image_base < start+length]
               for t in ('objdump','llvm-objdump')]
    other = {i.address:canonical(i) for i in streams[1]}
    a = streams[0]
    rows = []
    for j, ins in enumerate(a):
        m = re.fullmatch(r'qwordptr\[rax\+(0x[0-9a-f]+)\]', canonical(ins)[1])
        if ins.mnemonic != 'call' or not m or j < 2 or j+1 >= len(a):
            continue
        site = ins.address-pe.image_base
        slot = int(m[1],16)
        if slot > 0x78 or slot % 8 or a[j+1].address != ins.address+3:
            continue
        if raw[site-start:site-start+3] != bytes((0xff,0x50,slot)):
            continue
        # Allow precisely one pointer increment in rax before result store.
        end = j+1
        if end+1 < len(a) and canonical(a[end]) == ('lea','rax,[rbx+0x4]'):
            end += 1
        if canonical(a[end]) != ('movss','dwordptr[rbx],xmm0'):
            continue
        before = [canonical(x) for x in a[j-2:j]]
        if set(before) != {('mov','rax,qwordptr[rcx]'),('mulss','xmm1,dwordptr[rbx]')}:
            continue
        scope = a[j-2:end+1]
        if any(other.get(x.address)!=canonical(x) for x in scope):
            continue
        # Verify complete byte forms, not just matching disassembly text.
        expected = {('mov','rax,qwordptr[rcx]'):b'\x48\x8b\x01',
                    ('mulss','xmm1,dwordptr[rbx]'):b'\xf3\x0f\x59\x0b',
                    ('movss','dwordptr[rbx],xmm0'):b'\xf3\x0f\x11\x03',
                    ('lea','rax,[rbx+0x4]'):b'\x48\x8d\x43\x04',
                    canonical(ins):bytes((0xff,0x50,slot))}
        if any(raw[x.address-pe.image_base-start:x.address-pe.image_base-start+len(expected[canonical(x)])]!=expected[canonical(x)] for x in scope):
            continue
        if any(y.address-x.address!=len(expected[canonical(x)]) for x,y in zip(scope,scope[1:])):
            continue
        rows.append({'call_site':hex(site),'table_byte_offset':slot,'sample_store':hex(a[end].address-pe.image_base),
                     'sites':[hex(x.address-pe.image_base) for x in scope]})
    return {'start':hex(start),'bytes':length,'scope_sha256':hashlib.sha256(raw).hexdigest(),
            'candidates':rows,'limits':'Narrow local byte patterns only; no runtime target, reachability, or clipping law established.'}
