"""Read-only architecture and extracted-state inventory; no plugin execution."""
import argparse
import hashlib
import json
from pathlib import Path
from .pe import PE

MAX_INPUT = 256 * 1024 * 1024
LOADERS = {'loadlibrarya', 'loadlibraryw', 'loadlibraryexa', 'loadlibraryexw', 'getprocaddress'}


def bounded_pe(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_INPUT:
        raise ValueError('Expected bounded regular PE file')
    return PE(path)


def architecture(binary, siblings=()):
    """Explicit adjacent files only; a filename literal is not a load edge."""
    pe = bounded_pe(binary)
    siblings = [Path(p) for p in siblings]
    names = [p.name.casefold() for p in siblings]
    if len(names) > 64 or len(set(names)) != len(names):
        raise ValueError('Choose up to 64 distinct sibling names')
    imports = pe.imports().values()
    modules = sorted({x['dll'].casefold() for x in imports})
    loaders = sorted({x['symbol'] for x in imports if x['symbol'].casefold() in LOADERS})
    raw = pe.data.lower()
    edges = []
    for p, name in zip(siblings, names):
        if p.parent.resolve() != pe.path.parent.resolve() or p.resolve() == pe.path.resolve():
            raise ValueError('Candidate must be a distinct adjacent file')
        if p.suffix.casefold() not in {'.dll', '.vst3', '.epl'} or not name.isascii():
            raise ValueError('Expected ASCII plugin/engine filename')
        direct = name in modules
        literal = any(pattern in raw for pattern in (name.encode('ascii') + b'\0', name.encode('utf-16le') + b'\0\0'))
        child = bounded_pe(p)
        edges.append({'name': p.name, 'sha256': child.sha256, 'image_base': hex(child.image_base),
                      'static_import': direct, 'filename_literal_candidate': literal,
                      'status': 'STATIC_IMPORT' if direct else 'LITERAL_ONLY' if literal else 'NO_EDGE_OBSERVED'})
    return {'schema_version': 1, 'source': pe.path.name, 'sha256': pe.sha256,
            'image_base': hex(pe.image_base), 'imported_modules': modules,
            'loader_api_imports': loaders, 'adjacent_candidates': edges,
            'limits': 'Ordinary imports and raw filename substrings only; dynamic and delay-load edges, DSP roles, and runtime calls unverified.'}


def state_corpus(paths, size, fields=()):
    """Audit already extracted state blobs using analyst-declared byte spans."""
    paths = [Path(p) for p in paths]
    if not 1 <= len(paths) <= 4096 or type(size) is not int or not 1 <= size <= 1024 * 1024:
        raise ValueError('Invalid corpus bounds')
    if size * len(paths) > MAX_INPUT:
        raise ValueError('Corpus byte budget exceeded')
    coverage = bytearray(size)
    for field in fields:
        offset, length = field['offset'], field['length']
        if type(offset) is not int or type(length) is not int or not 0 <= offset < size or not 1 <= length <= size-offset:
            raise ValueError('Invalid field span')
        if any(coverage[offset:offset+length]):
            raise ValueError('Overlapping field spans')
        coverage[offset:offset+length] = bytes([1 if field.get('kind') == 'mapped' else 2]) * length
    hashes = set()
    rejected = 0
    varying = bytearray(size)
    first = None
    for p in paths:
        if p.is_symlink() or not p.is_file() or p.stat().st_size != size:
            rejected += 1
            continue
        raw = p.read_bytes()
        if len(raw) != size:
            rejected += 1
            continue
        hashes.add(hashlib.sha256(raw).hexdigest())
        if first is None:
            first = raw
        else:
            for i, (a, b) in enumerate(zip(first, raw)):
                varying[i] |= int(a != b)
    return {'schema_version': 1, 'records': len(paths), 'matching_size': len(paths)-rejected,
            'rejected_size_or_file': rejected, 'unique_matching_contents': len(hashes),
            'expected_bytes': size, 'declared_mapped_bytes': coverage.count(1),
            'declared_opaque_bytes': coverage.count(2), 'unclassified_bytes': coverage.count(0),
            'varying_offsets': [i for i, v in enumerate(varying) if v],
            'limits': 'Extracted blobs only; declared spans are not verified parameter semantics. No raw states, paths or state hashes emitted.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='mode', required=True)
    a = sub.add_parser('architecture'); a.add_argument('binary'); a.add_argument('siblings', nargs='*')
    c = sub.add_parser('states'); c.add_argument('size', type=int); c.add_argument('paths', nargs='+'); c.add_argument('--fields', type=Path)
    args = p.parse_args()
    if args.mode == 'architecture':
        result = architecture(args.binary, args.siblings)
    else:
        if args.fields and args.fields.stat().st_size > 1024 * 1024:
            raise ValueError('Field schema too large')
        result = state_corpus(args.paths, args.size, json.loads(args.fields.read_text()) if args.fields else ())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
