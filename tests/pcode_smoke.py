"""Real Ghidra high-P-code validation on an owned compiled fixture only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from ghidra_smoke import fixture_exports


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ghidra-home',required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parent.parent
    analyzer=Path(a.ghidra_home)/'support'/'analyzeHeadless'
    with tempfile.TemporaryDirectory(prefix='skell-pcode-') as d:
        root=Path(d);obj=root/'fixture.obj';exe=root/'fixture.exe';out=root/'pcode.tsv'
        source=repo/'tests'/'fixtures'/'ghidra_fixture.c'
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-fno-stack-protector','-c',str(source),'-o',str(obj)],check=True,timeout=30)
        subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/out:'+str(exe),str(obj)],check=True,timeout=30)
        targets=fixture_exports(exe);before=exe.read_bytes();sha=hashlib.sha256(before).hexdigest()
        args=[str(analyzer),str(root),'PcodeOwned','-import',str(exe),'-analysisTimeoutPerFile','120','-max-cpu','2','-scriptPath',str(repo/'skell_vst_decompiler'/'ghidra_scripts'),'-postScript','SkellPcodeSummary.java',str(out),sha,*[hex(v) for v in targets.values()],'-deleteProject']
        run=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240)
        if run.returncode or not out.is_file():raise RuntimeError(run.stdout[-18000:])
        lines=out.read_text().splitlines()
        if lines[0]!='SKELL_SHA256\t'+sha or lines[-1]!='SKELL_COMPLETE':raise RuntimeError('Incomplete or wrong source')
        reports={}
        for line in lines[1:-1]:
            addr,total,defs,*counts=line.split('\t');name=next(k for k,v in targets.items() if v==int(addr,16))
            if name in reports:raise RuntimeError('Duplicate result')
            counts={k:int(v) for k,v in (x.split('=') for x in counts)}
            if sum(counts.values())!=int(total) or int(defs)<=0:raise RuntimeError('Invalid data-flow counts')
            reports[name]={'operations':int(total),'defined_input_edges':int(defs),'opcodes':counts}
        if set(reports)!=set(targets):raise RuntimeError('Missing entries')
        for op in ('FLOAT_ADD','FLOAT_SUB','FLOAT_MULT'):
            if reports['smooth']['opcodes'].get(op,0)<1:raise RuntimeError('Missing known arithmetic '+op)
        if not reports['apply_gain']['opcodes'].get('FLOAT_MULT') or not reports['apply_gain']['opcodes'].get('CALL'):raise RuntimeError('Missing gain or call evidence')
        if exe.read_bytes()!=before:raise RuntimeError('Fixture changed')
        print('SKELL_PCODE_RESULT '+json.dumps({'binary_sha256':sha,'functions':reports},sort_keys=True))


if __name__=='__main__':main()
