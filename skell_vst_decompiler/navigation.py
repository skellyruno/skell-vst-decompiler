"""PE x64 unwind ranges and bounded native cross-reference navigation.
Unwind entries are compiler metadata, not guaranteed logical function boundaries.
"""
from bisect import bisect_right
import re
import struct
from .pe import PEFormatError
from .disasm import disassemble, direct_calls, imported_call_sites


def runtime_ranges(pe):
    rva, size = pe.exception_directory
    if not rva and not size:
        return []
    if not rva or size % 12 or not 0 < size <= 12*500000:
        raise PEFormatError('Invalid x64 exception directory')
    raw = pe.at_rva(rva,size)
    entries=[]
    previous=-1
    for start,end,unwind in struct.iter_unpack('<III',raw):
        if not start < end or start < previous or not unwind:
            raise PEFormatError('Invalid or unsorted runtime function range')
        pe.at_rva(start,end-start,executable=True)
        pe.at_rva(unwind,1)
        entries.append((start,end,unwind))
        previous=end
    return entries


def containing_range(entries,rva):
    i=bisect_right(entries,(rva,1<<32,1<<32))-1
    if i>=0 and entries[i][0]<=rva<entries[i][1]:
        start,end,unwind=entries[i]
        return {'start_rva':hex(start),'end_rva_exclusive':hex(end),'unwind_rva':hex(unwind),'bytes':end-start}
    return None


def function_report(pe,rva,objdump='objdump'):
    entries=runtime_ranges(pe)
    region=containing_range(entries,rva)
    if region is None:
        return {'binary_sha256':pe.sha256,'query_rva':hex(rva),'region':None,'note':'No covering unwind record; leaf functions may have no record.'}
    start=int(region['start_rva'],16)
    n=region['bytes']
    result={'binary_sha256':pe.sha256,'query_rva':hex(rva),'region':region,'runtime_record_count':len(entries)}
    if n<=32768:
        instructions=disassemble(pe,start,n,objdump)
        result.update(direct_calls=direct_calls(pe,instructions),import_calls=imported_call_sites(pe,instructions),instruction_count=len(instructions))
    else:result['note']='Range exceeds bounded disassembly size; request a smaller window.'
    return result


def scan_refs(pe, instructions, target, length=1, entries=None):
    """References to an RVA interval from decoded instructions, not raw byte matches."""
    if target<0 or not 1<=length<=65536:raise ValueError('Invalid reference interval')
    if entries is None:entries=[]
    result=[]
    for ins in instructions:
        op=ins.operands
        match=re.search(r'#\s*0x([0-9a-fA-F]+)',op) if '[rip' in op else None
        kind='rip-relative'
        if match is None and (ins.mnemonic=='call' or ins.mnemonic.startswith('j')):
            match=re.fullmatch(r'0x([0-9a-fA-F]+)',op)
            kind='direct-control-flow'
        if match is None:continue
        dest=int(match.group(1),16)-pe.image_base
        if target<=dest<target+length:
            site=ins.address-pe.image_base
            result.append({'site_rva':hex(site),'target_rva':hex(dest),'kind':kind,'mnemonic':ins.mnemonic,'containing_range':containing_range(entries,site)})
    return result


def reference_report(pe,start,length,target,target_length=1,objdump='objdump'):
    instructions=disassemble(pe,start,length,objdump)
    entries=runtime_ranges(pe)
    return {'binary_sha256':pe.sha256,'scan_start_rva':hex(start),'scan_bytes':length,'target_rva':hex(target),'target_bytes':target_length,'references':scan_refs(pe,instructions,target,target_length,entries),'limits':'Only decoded RIP-relative references and direct branches in the requested range. No indirect call or register-based dataflow inference.'}
