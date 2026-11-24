"""Bounded local GNU/LLVM observation batches for owned research fixtures."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from .analysis_cache import encode, read_bytes, sha
from .engine_agreement import call_observations
from .pe import PE
from .cache_policy import prune_cache, validate_limits
from .dependency_identity import linux_dependencies

ENGINES = ('objdump', 'llvm-objdump')
MAX_SCOPES = 64


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def engine_identity(name, *, track_dependencies=False):
    if name not in ENGINES:
        raise ValueError('Unsupported analyzer')
    found = shutil.which(name)
    if not found:
        raise FileNotFoundError(name)
    path = Path(found).resolve()
    version = subprocess.check_output([str(path), '--version'], text=True, timeout=10)
    identity = {'name': name, 'path': str(path), 'sha256': file_hash(path), 'version': version}
    if track_dependencies:
        identity['dependencies'] = linux_dependencies(path)
    return identity


def agreement(observations):
    """No votes for missing data; preserve each engine's observation."""
    if not observations:
        raise ValueError('No observations')
    scope = tuple(observations[0][k] for k in ('sha256', 'start', 'size'))
    names = [o['engine'] for o in observations]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate analyzer identity')
    if any(tuple(o[k] for k in ('sha256','start','size')) != scope for o in observations):
        raise ValueError('Source or scope mismatch')
    maps = {o['engine']: o['calls'] for o in observations}
    result = []
    for site in sorted(set().union(*(m.keys() for m in maps.values())), key=lambda x: int(x,16)):
        votes = {name: m.get(site) for name,m in maps.items()}
        known = {v for v in votes.values() if v is not None}
        count = sum(v is not None for v in votes.values())
        status = ('conflict' if len(known)>1 else 'single_observation' if count==1 else
                  'agreed_static' if count==len(maps) else 'partial_agreement')
        result.append({'site_rva':site, 'observations':votes, 'support':count,
                       'engines':len(maps), 'status':status})
    return result


def cached_observation(pe, scope, tool, code, cache_dir, environment_id):
    start,size = scope
    identity = {'schema':1,'binary':pe.sha256,'scope':[start,size], 'engine':tool,
                'code':code,'python':list(sys.version_info[:3]), 'environment':environment_id}
    key = sha(encode(identity))
    entry = cache_dir / (key+'.json') if cache_dir is not None else None
    if entry is not None:
        try:
            if entry.is_symlink():
                raise ValueError('Symlink cache entry')
            envelope = json.loads(read_bytes(entry))
            observation = envelope['observation']
            if envelope['identity']==identity and envelope['digest']==sha(encode(observation)):
                if (observation['sha256'],observation['start'],observation['size'],observation['engine']) == (pe.sha256,start,size,tool['name']):
                    return observation, True
        except (OSError, ValueError, KeyError, TypeError):
            pass
    observation = call_observations(pe,start,size,tool['path'])
    observation['engine'] = tool['name']
    observation['calls'] = {hex(k):hex(v) for k,v in observation['calls'].items()}
    if entry is not None:
        payload = encode({'identity':identity,'observation':observation,'digest':sha(encode(observation))})
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(dir=entry.parent,delete=False) as stream:
                tmp = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp,entry)
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)
    return observation,False


def run_batch(binary, scopes, *, workers=2, cache_dir=None, environment_id=None,
              cache_limits=None, track_dependencies=False):
    """At most two concurrent external processes; caller supplies environment ID.

    Change environment_id whenever system/shared libraries or tool settings change.
    Cache is optional and intended for trusted local storage only.
    """
    if type(workers) is not int or not 1<=workers<=2:
        raise ValueError('Choose one or two workers')
    if cache_dir is not None and (not isinstance(environment_id,str) or not environment_id.strip()):
        raise ValueError('Cache requires explicit environment identity')
    if cache_limits is not None:
        if cache_dir is None:
            raise ValueError('Cache limits require a cache directory')
        validate_limits(*cache_limits)
    scopes = list(scopes)
    if not 1<=len(scopes)<=MAX_SCOPES or len(set(scopes))!=len(scopes):
        raise ValueError('Choose 1..64 distinct scopes')
    pe = PE(binary)
    for start,size in scopes:
        if type(start) is not int or type(size) is not int or not 1<=size<=32768:
            raise ValueError('Invalid bounded scope')
        pe.at_rva(start,size,executable=True)
    tools = [engine_identity(name, track_dependencies=track_dependencies) for name in ENGINES]
    source = Path(__file__).parent
    code = {name:file_hash(source/name) for name in ('engine_batch.py','engine_agreement.py','analysis_cache.py','disasm.py','pe.py','cache_policy.py','dependency_identity.py')}
    root = Path(cache_dir).resolve() if cache_dir is not None else None
    if root is not None:
        root.mkdir(parents=True,exist_ok=True,mode=0o700)
    # Copy the exact input to a private isolated temporary file: no execution.
    with tempfile.TemporaryDirectory(prefix='skell-engine-') as tmp:
        path = Path(tmp)/'input.exe'
        path.write_bytes(pe.data)
        frozen = PE(path)
        if frozen.sha256 != pe.sha256:
            raise RuntimeError('Source snapshot changed')
        jobs = [(scope,tool) for scope in scopes for tool in tools]
        def work(job):
            return cached_observation(frozen,job[0],job[1],code,root,environment_id)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(work,jobs))
    if file_hash(binary)!=pe.sha256 or any(file_hash(t['path'])!=t['sha256'] for t in tools):
        raise RuntimeError('Input or analyzer changed during batch')
    if track_dependencies and any(linux_dependencies(t['path']) != t['dependencies'] for t in tools):
        raise RuntimeError('Analyzer dependencies changed during batch')
    maintenance = prune_cache(root,max_entries=cache_limits[0],max_bytes=cache_limits[1]) if cache_limits is not None else None
    rows = []
    for i,scope in enumerate(scopes):
        pair = [o for o,_ in results[2*i:2*i+2]]
        rows.append({'start':scope[0],'size':scope[1],'checks':agreement(pair)})
    return {'binary_sha256':pe.sha256,'scopes':rows,'engines':tools,
            'cache_hits':sum(hit for _,hit in results),'jobs':len(jobs),
            'cache_maintenance':maintenance,
            'note':'Static direct-call agreement only; missing observations are not negatives.'}
