"""Bounded external PE import observation; never executes the inspected file."""
import hashlib
import json
import re

SHA=re.compile(r'[0-9a-f]{64}\Z')
MAX_BYTES=8_000_000


def normalize(raw,expected_sha,expected_size):
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES or not SHA.fullmatch(expected_sha):
        raise ValueError('Invalid bounded evidence request')
    e=json.loads(raw)
    if not isinstance(e,dict) or e.get('operation')!='inspect_pe_imports':
        raise ValueError('Wrong evidence operation')
    identity=e.get('subject',{}).get('identity',{})
    result=e.get('normalized_result',{})
    artifact=result.get('artifact',{})
    if identity.get('sha256')!=expected_sha or artifact.get('sha256')!=expected_sha or artifact.get('bytes')!=expected_size:
        raise ValueError('Source mismatch')
    if result.get('coverage',{}).get('status')!='complete' or result.get('issues')!=[]:
        raise ValueError('Incomplete import observation')
    bits=result.get('bits')
    if (bits,result.get('machine'),result.get('format')) not in ((32,0x14c,'pe32'),(64,0x8664,'pe32-plus')):
        raise ValueError('Unsupported PE architecture')
    rows=[]
    for key in ('imports','delay_imports'):
        ds=result.get(key)
        if not isinstance(ds,list) or len(ds)>256:
            raise ValueError('Descriptor bound')
        count=0
        for d in ds:
            name=d.get('name')
            funcs=d.get('functions')
            if not isinstance(name,str) or not name or not isinstance(funcs,list):
                raise ValueError('Invalid descriptor')
            for f in funcs:
                sym,ordinal,rva=f.get('name'),f.get('ordinal'),f.get('iat_rva')
                if ((isinstance(sym,str) and bool(sym)) == (type(ordinal) is int and 0<=ordinal<=65535)
                    or type(rva) is not int or not 0<=rva<2**32):
                    raise ValueError('Invalid import entry')
                count+=1
                rows.append((key,name.lower(),sym,ordinal,rva))
                if len(rows)>8192:raise ValueError('Import bound')
        if count!=result['coverage'][key]:
            raise ValueError('Coverage count mismatch')
    if len(result['imports'])+len(result['delay_imports'])!=result['coverage'].get('examined_dlls'):
        raise ValueError('Descriptor count mismatch')
    eid=e.get('evidence_id')
    if not isinstance(eid,str) or not re.fullmatch(r'ev_[0-9a-f]{64}',eid):
        raise ValueError('Evidence ID syntax')
    digest=result.get('imphash',{}).get('md5')
    if digest is not None and (not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{32}',digest)):
        raise ValueError('Invalid import hash')
    # Keep names in memory only for owned-fixture comparison.
    return {'bits':bits,'rows':sorted(rows,key=repr),'imphash':digest,
            'binary_sha256':expected_sha,'document_sha256':hashlib.sha256(raw).hexdigest(),
            'evidence_id':eid,'status':'external_metadata_observation'}
