"""Run four analyzers and Revenant on one freshly compiled, owned PE."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from ghidra_smoke import fixture_exports
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.navigation import runtime_ranges, containing_range
from skell_vst_decompiler.ghidra_bridge import make_plan, run_analysis
from skell_vst_decompiler.classgraph import compare_rizin
from skell_vst_decompiler.engine_agreement import call_observations
from skell_vst_decompiler.multi_engine import reconcile_observations
from skell_vst_decompiler.verification import revenant_metadata


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ghidra-home',required=True)
    p.add_argument('--rizin',required=True)
    p.add_argument('--revenant',required=True)
    a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='skell-unified-') as d:
        root=Path(d); obj=root/'fixture.obj'; exe=root/'fixture.exe'
        src=Path(__file__).parent/'fixtures'/'ghidra_fixture.c'
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-fno-stack-protector','-c',str(src),'-o',str(obj)],check=True,timeout=30)
        subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/out:'+str(exe),str(obj)],check=True,timeout=30)
        pe=PE(exe); exports=fixture_exports(exe); start=exports['apply_gain']
        span=containing_range(runtime_ranges(pe),start)
        if not span or int(span['start_rva'],16)!=start:
            raise RuntimeError('Missing exact fixture unwind start')
        documents=[]
        def add(engine, observations):
            documents.append({'engine':engine,'binary_sha256':pe.sha256,'observations':observations})
        def obs(kind, subject, value):
            return {'kind':kind,'subject':subject,'value':value}
        direct_sites={}
        for engine in ('objdump','llvm-objdump'):
            data=call_observations(pe,start,span['bytes'],engine)
            direct_sites[engine]=data['calls']
            add(engine,[obs('function_call',start,target) for target in sorted(set(data['calls'].values()))])
        if direct_sites['objdump'] != direct_sites['llvm-objdump'] or exports['smooth'] not in direct_sites['objdump'].values():
            raise RuntimeError('Direct call site disagreement on owned fixture')
        rz=subprocess.run([a.rizin,'-q','-e','scr.color=0','-c','aaa;aflj',str(exe)],capture_output=True,text=True,timeout=90,check=True)
        r=compare_rizin(pe,{'binary_sha256':pe.sha256,'image_base':pe.image_base,'functions':json.loads(rz.stdout)})
        entries={int(x['rva'],16) for x in r['functions'] if x['status']!='not_file_backed_executable'}
        if not set(exports.values())<=entries:
            raise RuntimeError('Rizin did not recover both exports')
        add('rizin',[obs('function_entry',x,x) for x in sorted(entries)])
        plan=make_plan(pe,exports.values())
        g=run_analysis(pe,plan,a.ghidra_home,root/'ghidra',120)
        if g['status']!='complete' or g['binary_sha256']!=pe.sha256:
            raise RuntimeError('Ghidra result incomplete or mismatched')
        g_entries={int(x['entry_rva'],16) for x in g['targets'] if x['status']=='ok'}
        g_edges={(int(x['entry_rva'],16),int(x['related_rva'],16)) for x in g['call_links'] if x['kind']=='calls'}
        add('ghidra',[obs('function_entry',x,x) for x in sorted(g_entries)]+[obs('function_call',x,y) for x,y in sorted(g_edges)])
        combined=reconcile_observations(pe.sha256,documents)
        for x in exports.values():
            if not any(row['kind']=='function_entry' and row['subject_rva']==hex(x) and set(row['supporting_engines'])=={'rizin','ghidra'} for row in combined['claims']):
                raise RuntimeError('Expected export entry not corroborated')
        if not any(row['kind']=='function_call' and row['subject_rva']==hex(start) and row['value_rva']==hex(exports['smooth']) and set(row['supporting_engines'])=={'objdump','llvm-objdump','ghidra'} for row in combined['claims']):
            raise RuntimeError('Expected call edge not corroborated')
        # Revenant uses a separate metadata domain. No external provider, no
        # reimplementation, emulation, or decompilation stage.
        out=root/'revenant'
        subprocess.run([a.revenant,'analyze',str(exe),'--mode','software','--provider','none','--no-agentic','--no-tui','--no-verify','--no-cache','--fast','--only','recon','triage','extract','disasm','-o',str(out),'-j','2'],cwd=root,check=True,timeout=120)
        raw=json.loads((out/'report.json').read_text(encoding='utf-8'))
        meta=revenant_metadata(raw,pe.sha256)
        if not {'recon','triage','extract','disasm'}<=set(raw['stages_completed']) or meta['failed_stage_count'] or meta['function_count']<2:
            raise RuntimeError('Revenant static pipeline incomplete')
        if PE(exe).sha256!=pe.sha256:
            raise RuntimeError('Fixture changed')
        combined['revenant']=meta
        combined['exports']=exports
        combined['direct_call_sites']={k:{hex(x):hex(y) for x,y in v.items()} for k,v in direct_sites.items()}
        print('SKELL_UNIFIED_RESULT '+json.dumps(combined,sort_keys=True))


if __name__=='__main__':
    main()
