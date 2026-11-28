"""Exact-scope caller context and byte-backed x64 dispatch, no target execution."""
import hashlib
import re
import struct
from .pe import PEFormatError
from .disasm import disassemble
from .function_roles import role_evidence
from .navigation import runtime_ranges


def edges(pe, instructions, start, end):
    """Verify relative branches and RIP pointer slots against original bytes.

    Pointer slots are file-image candidates only, never proven runtime dispatch.
    Unresolved register/vtable calls are counted rather than guessed.
    """
    result=[]; unresolved=0
    for i in instructions:
        if i.mnemonic not in ('call','jmp'):continue
        site=i.address-pe.image_base
        if not start<=site<end:raise ValueError('Instruction outside scope')
        try:
            raw=pe.at_rva(site,min(6,end-site),executable=True)
            if len(raw)>=5 and raw[0]==(0xe8 if i.mnemonic=='call' else 0xe9):
                target=site+5+struct.unpack_from('<i',raw,1)[0]
                kind='relative_call' if i.mnemonic=='call' else 'relative_jump'
            elif len(raw)>=2 and raw[0]==0xeb and i.mnemonic=='jmp':
                target=site+2+struct.unpack_from('<b',raw,1)[0];kind='relative_jump'
            elif len(raw)>=6 and raw[:2]==(b'\xff\x15' if i.mnemonic=='call' else b'\xff\x25'):
                slot=site+6+struct.unpack_from('<i',raw,2)[0]
                target=struct.unpack('<Q',pe.at_rva(slot,8))[0]-pe.image_base
                try:pe.at_rva(target,1,executable=True)
                except PEFormatError:target=None
                result.append(dict(site=site,kind='file_pointer_slot',slot=slot,target=target));continue
            else:unresolved+=1;continue
            # Require the textual decoder target to agree with the byte displacement.
            m=re.fullmatch(r'(?:0x)?([0-9a-fA-F]+)(?:\s+<[^>]+>)?',i.operands.strip())
            if not m or int(m[1],16)-pe.image_base!=target:raise ValueError('Relative target disagreement')
            pe.at_rva(target,1,executable=True)
            if kind=='relative_jump' and start<=target<end:continue
            result.append(dict(site=site,kind=kind,target=target))
        except PEFormatError:unresolved+=1
    return result,unresolved


def context(rows, links, roots):
    """Reachability from explicitly labeled roots, not inferred processor roles."""
    nodes={r['start_rva'] for r in rows}
    if not roots or set(roots)-nodes or any(v not in ('audio','setup','utility') for v in roots.values()):
        raise ValueError('Invalid explicit root roles')
    adj={n:set() for n in nodes}
    for a,b in links:
        if a in nodes and b in nodes:adj[a].add(b)
    seen={n:set() for n in nodes}
    for root,role in roots.items():
        stack=[root];visited=set()
        while stack:
            n=stack.pop()
            if n in visited:continue
            visited.add(n);seen[n].add(role);stack.extend(adj[n]-visited)
    out=[]
    for r in rows:
        roles=sorted(seen[r['start_rva']]);local=r['local_role_evidence']['role']
        status=('AUDIO_CONTEXT_CANDIDATE' if roles==['audio'] and local=='PROCESSING_CANDIDATE' else
                'NON_AUDIO_CONTEXT_ONLY' if roles and 'audio' not in roles else 'UNRESOLVED')
        out.append({**r,'observed_root_contexts':roles,'context_status':status})
    return out


def review(pe, expected_sha256, starts, roots, tools=('objdump','llvm-objdump')):
    if pe.sha256!=expected_sha256 or not 1<=len(starts)<=128 or len(set(starts))!=len(starts):
        raise ValueError('Source or scope mismatch')
    if not tools or any(t not in ('objdump','llvm-objdump') for t in tools):raise ValueError('Invalid decoder')
    ranges={a:b for a,b,_ in runtime_ranges(pe)};rows=[];links=[];all_edges=[]
    for a in starts:
        b=ranges.get(a,0)
        if not 1<=b-a<=32768:raise ValueError('Require complete bounded unwind scope')
        decoded=[disassemble(pe,a,b-a,t) for t in tools]
        evidence=[edges(pe,x,a,b) for x in decoded]
        common=[e for e in evidence[0][0] if all(e in v[0] for v in evidence[1:])]
        local=[role_evidence(x) for x in decoded]
        role=local[0] if all(x['role']==local[0]['role'] for x in local) else {'role':'UNRESOLVED','features':{}}
        row={'start_rva':a,'end_rva':b,'region_sha256':hashlib.sha256(pe.at_rva(a,b-a,executable=True)).hexdigest(),
             'local_role_evidence':role,'unresolved_control_transfers':[x[1] for x in evidence],
             'decoder_edge_counts':[len(x[0]) for x in evidence],'agreed_edge_count':len(common)}
        rows.append(row)
        for e in common:
            all_edges.append({'caller':a,**e})
            if e['kind']!='file_pointer_slot':links.append((a,e['target']))
    if hashlib.sha256(pe.path.read_bytes()).hexdigest()!=expected_sha256:raise ValueError('Source changed')
    return {'binary_sha256':expected_sha256,'decoders':list(tools),'scopes':context(rows,links,roots),'edges':all_edges,
            'limits':'Explicit root labels, selected complete unwind regions only. Reachability is static, not execution; unknown and mixed context remain unresolved. Pointer-slot edges excluded from reachability.'}


def review_manifest(path, manifest, tools=('objdump','llvm-objdump')):
    from pathlib import Path
    from .pe import PE
    path=Path(path)
    if not path.is_file() or path.is_symlink() or not 0<path.stat().st_size<=256*1024*1024:
        raise ValueError('Expected bounded PE module')
    if not isinstance(manifest,dict) or set(manifest)!={'binary_sha256','scopes','roots'}:
        raise ValueError('Invalid context manifest')
    starts=manifest['scopes'];raw_roots=manifest['roots']
    if not isinstance(starts,list) or not 1<=len(starts)<=128 or any(type(s) is not int or not 0<=s<2**32 for s in starts):
        raise ValueError('Invalid context scopes')
    if not isinstance(raw_roots,list) or not 1<=len(raw_roots)<=len(starts):raise ValueError('Invalid context roots')
    roots={}
    for row in raw_roots:
        if not isinstance(row,dict) or set(row)!={'start_rva','role'} or type(row['start_rva']) is not int or row['start_rva'] in roots or row['role'] not in ('audio','setup','utility'):
            raise ValueError('Invalid context root')
        roots[row['start_rva']]=row['role']
    return review(PE(path),manifest['binary_sha256'],starts,roots,tools)


def main():
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('module');p.add_argument('manifest',type=Path)
    a=p.parse_args()
    if not 0<a.manifest.stat().st_size<=65536:raise ValueError('Context manifest exceeds bound')
    print(json.dumps(review_manifest(a.module,json.loads(a.manifest.read_text())),indent=2,allow_nan=False))

if __name__=='__main__':main()
