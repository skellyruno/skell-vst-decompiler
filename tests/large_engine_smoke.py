"""64 distinct original DSP fixture functions; static analysis, never execute PE."""
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
    with tempfile.TemporaryDirectory(prefix='skell-large-') as d:
        root=Path(d); source=root/'large.c'; obj=root/'large.obj'; exe=root/'large.exe'
        names=[f'probe_{i:02d}' for i in range(64)]
        lines=['__declspec(dllexport) __declspec(noinline) double smooth(double s,double t,double a){return s+(t-s)*a;}']
        for i,name in enumerate(names):
            lines.append(f'__declspec(dllexport) __declspec(noinline) double {name}(double x,double s,double t){{return x*smooth(s,t,{(i+1)/128.0:.10f});}}')
        lines += ['int _fltused=0;', 'volatile double result;', 'void entry(void){result=probe_00(.5,.1,.9);}']
        source.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O1','-fno-stack-protector','-c',str(source),'-o',str(obj)],check=True,timeout=30)
        subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib','/opt:noicf','/Brepro','/out:'+str(exe),str(obj)],check=True,timeout=30)
        pe=PE(exe); exports=fixture_exports(exe, ['smooth',*names]); ranges=runtime_ranges(pe)
        scopes=[]
        for name in names:
            start=exports[name]; span=containing_range(ranges,start)
            if not span or int(span['start_rva'],16)!=start:
                raise RuntimeError('Missing owned probe unwind entry')
            scopes.append((start,span['bytes']))
        if len(set(scopes))!=64:
            raise RuntimeError('Probe functions not distinct')
        def measure(**kwargs):
            t=perf_counter(); result=run_batch(exe,scopes,**kwargs); return result,perf_counter()-t
        serial,ts=measure(workers=1)
        parallel,tp=measure(workers=2)
        common={'cache_dir':root/'cache','environment_id':'large-fixture-v1','track_dependencies':True}
        cold,tc=measure(**common)
        warm,tw=measure(**common,cache_limits=(64,64*1024*1024))
        partial,tr=measure(**common)
        if not serial['scopes']==parallel['scopes']==cold['scopes']==warm['scopes']==partial['scopes']:
            raise RuntimeError('Engine observations changed')
        if cold['cache_hits']!=0 or warm['cache_hits']!=128 or partial['cache_hits']!=64:
            raise RuntimeError('Unexpected cache hits')
        if not warm['cache_maintenance']['within_limits'] or warm['cache_maintenance']['remaining_entries']!=64:
            raise RuntimeError('Cache budget not enforced')
        for scope in serial['scopes']:
            checks=scope['checks']
            if len(checks)!=1 or checks[0]['status']!='agreed_static' or set(checks[0]['observations'].values())!={hex(exports['smooth'])}:
                raise RuntimeError('Owned probe call disagreement')
        print('SKELL_LARGE_RESULT '+json.dumps({'fixture_sha256':pe.sha256,'distinct_functions':len(scopes),
              'jobs':serial['jobs'],'serial_seconds':ts,'parallel_seconds':tp,
              'dependency_tracked_cold_seconds':tc,'dependency_tracked_warm_seconds':tw,
              'partial_cache_seconds':tr,'warm_hits':warm['cache_hits'],'partial_hits':partial['cache_hits'],
              'maintenance':warm['cache_maintenance'],'all_expected_edges_agreed':True,
              'dependency_counts':{t['name']:len(t['dependencies']) for t in cold['engines']}},sort_keys=True))

if __name__=='__main__':main()
