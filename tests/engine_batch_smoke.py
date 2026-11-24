"""Actual owned PE fixture: sequential, parallel, cold/warm and invalidation."""
import json
from pathlib import Path
import subprocess
import tempfile
from time import perf_counter
from ghidra_smoke import fixture_exports
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.navigation import runtime_ranges, containing_range
from skell_vst_decompiler.engine_batch import run_batch


def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); obj=root/'fixture.obj'; exe=root/'fixture.exe'
        source=Path(__file__).parent/'fixtures'/'ghidra_fixture.c'
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-fno-stack-protector','-c',str(source),'-o',str(obj)],check=True,timeout=30)
        subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/out:'+str(exe),str(obj)],check=True,timeout=30)
        pe=PE(exe); exports=fixture_exports(exe); start=exports['apply_gain']
        span=containing_range(runtime_ranges(pe),start)
        scopes=[(start,span['bytes'])]
        # Distinct bounded ranges of the same owned function for workload measurement.
        scopes.extend((start,n) for n in range(1,span['bytes']) if n>=32)
        def measure(**kwargs):
            t=perf_counter(); result=run_batch(exe,scopes,**kwargs); return result,perf_counter()-t
        a,seq=measure(workers=1)
        b,parallel=measure(workers=2)
        c,cold=measure(cache_dir=root/'cache',environment_id='fixture-v1')
        e,warm=measure(cache_dir=root/'cache',environment_id='fixture-v1')
        f,_=measure(cache_dir=root/'cache',environment_id='fixture-v2')
        assert a['scopes']==b['scopes']==c['scopes']==e['scopes']==f['scopes']
        assert c['cache_hits']==f['cache_hits']==0 and e['cache_hits']==e['jobs']
        assert any(x['status']=='agreed_static' and hex(exports['smooth']) in x['observations'].values() for x in a['scopes'][0]['checks'])
        entry=next((root/'cache').glob('*.json')); entry.write_text('{bad')
        # Different environment keys coexist; test both until the corrupted one is encountered.
        g,_=measure(cache_dir=root/'cache',environment_id='fixture-v1')
        h,_=measure(cache_dir=root/'cache',environment_id='fixture-v2')
        assert g['cache_hits']+h['cache_hits']==g['jobs']+h['jobs']-1
        print(json.dumps({'fixture_sha256':pe.sha256,'jobs':a['jobs'],'scope_count':len(scopes),
                          'sequential_seconds':seq,'parallel_seconds':parallel,'cold_seconds':cold,'warm_seconds':warm,
                          'cache_hits':e['cache_hits'],'same_observations':True,'first_scope':a['scopes'][0],
                          'engines':[{'name':t['name'],'version':t['version'].splitlines()[0]} for t in a['engines']]},indent=2))

if __name__=='__main__':main()
