"""Local content-addressed cache of structured report reconciliation only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

MAX_BYTES = 8_000_000


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bytes(path):
    with Path(path).open('rb') as f:
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Oversized report or cache entry')
    return raw


def reconcile_directory(reports, cache_dir=None):
    from .verification import reconcile
    root = Path(reports).resolve()
    raw = {p.name: read_bytes(p) for p in sorted(root.glob('*.json'))}
    snapshot_name = 'vmr_variant_navigation.json'
    if snapshot_name not in raw:
        raise ValueError('Missing variant snapshot')
    # Code and runtime are inputs, as well as every exact report byte.
    source = Path(__file__).parent
    identity = {'schema': 1, 'python': list(sys.version_info[:3]),
                'code': {name: sha((source / name).read_bytes()) for name in
                         ('analysis_cache.py', 'verification.py', 'interval_index.py')},
                'reports': {name: sha(data) for name, data in raw.items()}}
    key = sha(encode(identity))
    entry = None
    if cache_dir is not None:
        directory = Path(cache_dir).resolve()
        if directory == root or root in directory.parents:
            raise ValueError('Cache must be outside report directory')
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        entry = directory / (key + '.json')
        try:
            if entry.is_symlink():
                raise ValueError('Symlink cache entry')
            envelope = json.loads(read_bytes(entry))
            result = envelope['result']
            if (envelope['key'] == key and envelope['identity'] == identity
                    and envelope['result_sha256'] == sha(encode(result))
                    and result['snapshot_file_sha256'] == identity['reports'][snapshot_name]):
                return result, True
        except (OSError, ValueError, KeyError, TypeError):
            pass  # corrupt, stale or unavailable; recompute
    snapshot = json.loads(raw[snapshot_name])
    inputs = [(name, json.loads(data), identity['reports'][name])
              for name, data in raw.items() if name != snapshot_name]
    result = reconcile(snapshot, inputs)
    result['snapshot_file_sha256'] = identity['reports'][snapshot_name]
    if entry is not None:
        envelope = encode({'key': key, 'identity': identity, 'result': result,
                           'result_sha256': sha(encode(result))})
        if len(envelope) <= MAX_BYTES:
            tmp = None
            try:
                with tempfile.NamedTemporaryFile(dir=entry.parent, delete=False) as f:
                    tmp = Path(f.name)
                    f.write(envelope)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, entry)
            finally:
                if tmp is not None:
                    tmp.unlink(missing_ok=True)
    return result, False
