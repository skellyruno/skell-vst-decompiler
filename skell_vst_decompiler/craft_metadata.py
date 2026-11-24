"""Bounded metadata-only adapter for standalone Craft Anything layout evidence.

External results remain observations, not trusted instructions. No vendor
content, arbitrary commands, rebuilding, or automatic confidence promotion.
"""
import hashlib
import json
import re
from pathlib import Path

SHA=re.compile(r'[0-9a-f]{64}\Z')
EVIDENCE_ID=re.compile(r'ev_[0-9a-f]{64}\Z')
MAX_BYTES=8_000_000


def normalize(raw, expected_sha256):
    """Return a small allowlisted summary; do not copy external text/results."""
    if not isinstance(expected_sha256,str) or not SHA.fullmatch(expected_sha256):
        raise ValueError('Expected exact lowercase SHA-256')
    if not isinstance(raw,(bytes,bytearray)) or len(raw)>MAX_BYTES:
        raise ValueError('Expected bounded JSON bytes')
    e=json.loads(raw)
    if not isinstance(e,dict) or 'error' in e:
        raise ValueError('Expected successful layout evidence')
    subject=e.get('subject')
    if not isinstance(subject,dict) or subject.get('sha256')!=expected_sha256:
        raise ValueError('External source fingerprint mismatch')
    evidence_id=e.get('id')
    if not isinstance(evidence_id,str) or not EVIDENCE_ID.fullmatch(evidence_id):
        raise ValueError('Invalid external evidence ID')
    if e.get('operation')!='native_layout_show':
        raise ValueError('Unsupported external operation')
    env=e.get('environment')
    if not isinstance(env,dict) or env.get('engine')!='builtin':
        raise ValueError('Expected built-in metadata engine')
    result=e.get('result')
    if not isinstance(result,dict):
        raise ValueError('Missing layout result')
    bits=result.get('bits')
    if type(bits) is not int or bits not in (32,64) or result.get('format')!='pe':
        raise ValueError('Expected PE32 or PE32+ layout')
    base=result.get('image_base')
    if not isinstance(base,str) or not re.fullmatch(r'0x[0-9a-fA-F]{1,16}',base):
        raise ValueError('Invalid image base')
    base=int(base,16)
    if not 0<=base<2**bits:
        raise ValueError('Image base outside architecture range')
    sections=result.get('sections')
    if not isinstance(sections,list) or not 1<=len(sections)<=96 or any(not isinstance(s,dict) for s in sections):
        raise ValueError('Unexpected section table')
    linkage=result.get('linkage')
    exports=linkage.get('exports') if isinstance(linkage,dict) else None
    if type(exports) is not int or not 0<=exports<=65536:
        raise ValueError('Invalid export count')
    coverage=e.get('coverage')
    if not isinstance(coverage,dict) or coverage.get('status')!='complete':
        raise ValueError('Incomplete external layout evidence')
    return {'binary_sha256':expected_sha256,'external_evidence_id':evidence_id,
            'source_document_sha256':hashlib.sha256(raw).hexdigest(),
            'architecture':'x86' if bits==32 else 'x64',
            'image_base':hex(base),'section_count':len(sections),'export_count':exports,
            'status':'external_metadata_observation',
            'note':'Evidence ID syntax checked; content authenticity and DSP behavior not established.'}


def compare_owned(raw,binary):
    """Compare metadata on an explicitly owned fixture, not a runtime ABI test."""
    from .pe_export_audit import export_metadata
    from .pe import PE
    from .legacy_pe import LegacyPE
    path=Path(binary)
    native=export_metadata(path)
    external=normalize(raw,native['binary_sha256'])
    pe=LegacyPE(path) if native['architecture']=='x86' else PE(path)
    expected={'architecture':native['architecture'],'image_base':native['image_base'],
              'section_count':len(pe.sections),'export_count':native['named_count']}
    fields={k:{'native':v,'external':external[k]} for k,v in expected.items()}
    return {'external':external,'comparison':fields,
            'agreed':all(row['native']==row['external'] for row in fields.values()),
            'note':'Export count comparison restricted to owned fixtures with one named export per slot.'}
