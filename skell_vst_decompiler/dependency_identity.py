"""Linux dependency identity for trusted installed analyzer executables only."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def parse_ldd(output):
    paths = set()
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith('linux-vdso') or line.startswith('linux-gate'):
            continue
        if 'not found' in line:
            raise RuntimeError('Unresolved analyzer shared library')
        rhs = line.split(' => ',1)[-1]
        match = re.fullmatch(r'(/.+?)\s+\(0x[0-9a-fA-F]+\)',rhs)
        if not match:
            raise RuntimeError('Unrecognized ldd output')
        paths.add(str(Path(match[1]).resolve()))
    if not paths:
        raise RuntimeError('No dynamic libraries identified')
    return sorted(paths)


def linux_dependencies(executable):
    """Call ldd on a trusted system tool, NEVER on a target PE or untrusted file."""
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Automatic dependency tracking currently requires Linux')
    path=Path(executable)
    if not path.is_absolute() or not path.is_file():
        raise ValueError('Expected trusted installed analyzer path')
    # Use the system loader inspection utility. The caller has already resolved
    # a fixed GNU/LLVM analyzer name; this is not a general binary analyzer.
    out=subprocess.run(['/usr/bin/ldd',str(path)],capture_output=True,text=True,
                       timeout=15,check=True,env={**os.environ,'LC_ALL':'C'})
    return {p:file_hash(p) for p in parse_ldd(out.stdout)}
