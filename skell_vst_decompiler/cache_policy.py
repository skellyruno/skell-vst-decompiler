"""Optional bounded maintenance of verified, disposable Skell cache entries.

Use in a dedicated cache directory with no concurrent external writers.
Unknown files, symlinks, corrupted envelopes and research reports are untouched.
"""
import json
from pathlib import Path
import re
import stat
from .analysis_cache import encode, read_bytes, sha


def validate_limits(max_entries, max_bytes):
    if type(max_entries) is not int or type(max_bytes) is not int or max_entries < 0 or max_bytes < 0:
        raise ValueError('Nonnegative integer cache limits required')


def stable_stat(info):
    # Reading an entry may update atime. It is not a content mutation.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def verified_entry(path):
    if not re.fullmatch(r'[0-9a-f]{64}\.json', path.name):
        return None
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            return None
        data = json.loads(read_bytes(path))
        identity = data['identity']
        if not isinstance(identity,dict) or identity.get('schema') != 1 or sha(encode(identity)) != path.stem:
            return None
        if set(data) == {'identity','observation','digest'}:
            if not {'binary','scope','engine','code','python','environment'} <= identity.keys():
                return None
            valid = data['digest'] == sha(encode(data['observation']))
        elif set(data) == {'key','identity','result','result_sha256'}:
            if not {'reports','code','python'} <= identity.keys():
                return None
            valid = data['key'] == path.stem and data['result_sha256'] == sha(encode(data['result']))
        else:
            return None
        if not valid or stable_stat(before) != stable_stat(path.lstat()):
            return None
        return before
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def prune_cache(directory, *, max_entries, max_bytes):
    """Oldest-written first; only verified disposable entries count toward budget."""
    validate_limits(max_entries,max_bytes)
    root = Path(directory)
    if not root.is_dir():
        raise ValueError('Cache directory must exist')
    rows = []
    ignored = 0
    for path in root.iterdir():
        info = verified_entry(path)
        if info is None:
            ignored += 1
        else:
            rows.append((info.st_mtime_ns,path.name,info,path))
    rows.sort(key=lambda x:(x[0],x[1]))
    count, size = len(rows),sum(x[2].st_size for x in rows)
    removed = 0
    for _,_,info,path in rows:
        if count <= max_entries and size <= max_bytes:
            break
        # Do not unlink a changed/replaced file. Concurrent external writers
        # are unsupported; this is a best-effort guard, not a filesystem lock.
        try:
            if stable_stat(path.lstat()) != stable_stat(info):
                continue
            path.unlink()
        except OSError:
            continue
        count -= 1
        size -= info.st_size
        removed += 1
    return {'removed':removed,'remaining_entries':count,'remaining_bytes':size,
            'ignored_paths':ignored,'within_limits':count<=max_entries and size<=max_bytes}
