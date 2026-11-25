"""Optional Ghidra headless bridge. Runs the analyzer, never the target image.

Only authorized, local binaries. Generated pseudocode stays in a private work
folder. An analyzer result is a hypothesis, not verified DSP or original source.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from .pe import PE
from .navigation import containing_range, runtime_ranges
from .research_index import records, query, target_rvas

MAX_TARGETS = 64
SCRIPT = Path(__file__).resolve().parent / 'ghidra_scripts' / 'SkellExportSelected.java'


def make_plan(pe, rvas, reports=()):
    targets = set(rvas)
    for report in reports:
        if report.get('schema_version') != 1 or report.get('binary_sha256') != pe.sha256:
            raise ValueError('Evidence report must match the exact binary fingerprint')
        for region in report['regions']:
            targets.add(int(region['start_rva'], 16))
    if not 1 <= len(targets) <= MAX_TARGETS:
        raise ValueError('Select 1..64 distinct RVAs')
    ranges = runtime_ranges(pe)
    rows = []
    for rva in sorted(targets):
        pe.at_rva(rva, 1, executable=True)
        rows.append({'requested_rva': hex(rva), 'unwind_region': containing_range(ranges, rva)})
    return {'schema_version': 1, 'binary_sha256': pe.sha256, 'image_base': hex(pe.image_base),
            'targets': rows, 'note': 'Unwind ranges are hints; Ghidra must identify the enclosing function.'}


def launcher(home):
    path = Path(home).expanduser().resolve() / 'support' / ('analyzeHeadless.bat' if os.name == 'nt' else 'analyzeHeadless')
    if not path.is_file():
        raise FileNotFoundError(f'Install official Ghidra; analyzer not found: {path}')
    return path


def command(analyzer, project, binary, output, plan, seconds=300, *, retain_project=False):
    if not 1 <= seconds <= 3600:
        raise ValueError('Analysis time limit must be 1..3600 seconds')
    # No user-supplied Ghidra script or options; fixed script and isolated project.
    args = [str(analyzer), str(project), 'SkellResearch', '-import', str(binary),
            '-analysisTimeoutPerFile', str(seconds), '-max-cpu', '2',
            '-scriptPath', str(SCRIPT.parent), '-postScript', SCRIPT.name, str(output),
            plan['binary_sha256'], *(x['requested_rva'] for x in plan['targets'])]
    if not retain_project:
        args.append('-deleteProject')
    if os.name == 'nt' and any(re.search(r'[&|<>^%!\r\n"]', a) for a in args):
        raise ValueError('Windows batch launcher paths must not contain shell metacharacters')
    return args


def validate_output(folder, plan):
    manifest = folder / 'results.tsv'
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 100_000:
        raise RuntimeError('Missing or oversized analyzer manifest')
    lines = manifest.read_text(encoding='utf-8').splitlines()
    if not lines or lines[0] != 'SKELL_SHA256\t' + plan['binary_sha256'] or lines[-1] != 'SKELL_COMPLETE':
        raise RuntimeError('Missing completion marker or mismatched source fingerprint')
    expected = {int(x['requested_rva'], 16) for x in plan['targets']}
    seen = set()
    rows = []
    for line in lines[1:-1]:
        parts = line.split('\t')
        if len(parts) != 4:
            raise RuntimeError('Malformed result record')
        requested, entry, status, filename = parts
        if not re.fullmatch(r'0x[0-9a-f]{1,8}', requested):
            raise RuntimeError('Malformed requested RVA')
        rva = int(requested, 16)
        if rva not in expected or rva in seen:
            raise RuntimeError('Unexpected or repeated result address')
        seen.add(rva)
        if status not in {'ok', 'no_function', 'decompile_failed'}:
            raise RuntimeError('Unknown decompiler status')
        if entry != '-' and not re.fullmatch(r'0x[0-9a-f]{1,8}', entry):
            raise RuntimeError('Malformed entry RVA')
        if (status == 'no_function') != (entry == '-'):
            raise RuntimeError('Entry/status mismatch')
        if status == 'ok':
            if not re.fullmatch(r'function_[0-9a-f]+\.c\.txt', filename) or filename != f'function_{int(entry, 16):x}.c.txt':
                raise RuntimeError('Invalid pseudocode file name')
            path = folder / filename
            if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 8_000_000:
                raise RuntimeError('Missing or invalid pseudocode file')
        elif filename != '-':
            raise RuntimeError('Unexpected output for failed target')
        rows.append({'requested_rva': requested, 'entry_rva': None if entry == '-' else entry,
                     'status': status, 'local_pseudocode': None if filename == '-' else filename})
    if seen != expected:
        raise RuntimeError('Not all requested addresses were reported')
    links = validate_links(folder, rows)
    return {'binary_sha256': plan['binary_sha256'], 'targets': rows, 'call_links': links,
            'decompiled_target_count': sum(r['status'] == 'ok' for r in rows),
            'unique_decompiled_function_count': len({r['entry_rva'] for r in rows if r['status']=='ok'}),
            'status': 'complete' if all(r['status'] == 'ok' for r in rows) else 'partial',
            'note': 'C-like pseudocode is a local analysis candidate, not recovered original source.'}


def validate_links(folder, rows):
    """Only export verified-format local relationships, not inferred dynamic targets."""
    path = folder / 'calls.tsv'
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise RuntimeError('Missing or oversized call relationship manifest')
    lines = path.read_text(encoding='utf-8').splitlines()
    if not lines or lines[-1] != 'SKELL_COMPLETE':
        raise RuntimeError('Incomplete call relationship manifest')
    sources = {r['entry_rva'] for r in rows if r['status']=='ok'}
    links = []
    seen = set()
    for line in lines[:-1]:
        parts = line.split('\t')
        if len(parts)!=3 or parts[0] not in sources or parts[1] not in {'calls','called_by'} or not re.fullmatch(r'0x[0-9a-f]{1,8}',parts[2]):
            raise RuntimeError('Invalid call relationship')
        edge=tuple(parts)
        if edge in seen:
            raise RuntimeError('Duplicate call relationship')
        seen.add(edge)
        links.append({'entry_rva':parts[0],'kind':parts[1],'related_rva':parts[2]})
    return links


def run_analysis(pe, plan, home, work_root, seconds=300, *, retain_project=False):
    analyzer = launcher(home)
    if plan != make_plan(pe, [int(x['requested_rva'],16) for x in plan['targets']]):
        raise ValueError('Plan differs from source-validated targets')
    if not SCRIPT.is_file():
        raise RuntimeError('Missing packaged Ghidra script')
    root = Path(work_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    job = Path(tempfile.mkdtemp(prefix='skell-ghidra-', dir=root))
    project = job / 'project'; project.mkdir()
    output = job / 'private'; output.mkdir()
    (job / 'plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    args = command(analyzer, project, pe.path.resolve(), output, plan, seconds, retain_project=retain_project)
    # Merged streams avoid separate stdout/stderr pipe deadlocks. Unique project
    # ensures -deleteProject cannot remove a previous research project.
    with (job / 'analyzer.log').open('wb') as log:
        response = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT,
                                  timeout=seconds+len(plan['targets'])*35+120, check=False)
    if response.returncode != 0:
        raise RuntimeError(f'Ghidra failed; see {job / "analyzer.log"}')
    if PE(pe.path).sha256 != pe.sha256:
        raise RuntimeError('Source binary changed during analysis')
    result = validate_output(output, plan)
    for row in result['targets']:
        if row['entry_rva'] is not None:
            pe.at_rva(int(row['entry_rva'],16),1,executable=True)
    for edge in result['call_links']:
        pe.at_rva(int(edge['related_rva'],16),1,executable=True)
    result['project_retention_requested'] = retain_project
    (job / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return {'job': str(job), **result}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary', type=Path)
    p.add_argument('--rva', type=lambda v: int(v, 0), action='append', default=[])
    p.add_argument('--report', type=Path, action='append', default=[])
    p.add_argument('--catalog-dir', type=Path, help='Find regions across evidence JSON files')
    p.add_argument('--query', default='', help='Filter catalog evidence by keywords')
    p.add_argument('--ghidra-home', type=Path, help='Installed official Ghidra; omit to produce a plan only')
    p.add_argument('--work-root', type=Path, default=Path('local/ghidra'))
    p.add_argument('--retain-project', action='store_true', help='Keep isolated private Ghidra project for manual continuation')
    p.add_argument('--seconds', type=int, default=300)
    a = p.parse_args(argv)
    pe = PE(a.binary)
    targets = list(a.rva)
    if a.catalog_dir:
        selected = query(records(a.catalog_dir.glob('*.json')), a.query, pe.sha256)
        targets.extend(target_rvas(selected, pe.sha256))
    elif a.query:
        p.error('--query requires --catalog-dir')
    plan = make_plan(pe, targets, [json.loads(x.read_text(encoding='utf-8')) for x in a.report])
    result = run_analysis(pe, plan, a.ghidra_home, a.work_root, a.seconds, retain_project=a.retain_project) if a.ghidra_home else plan
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
