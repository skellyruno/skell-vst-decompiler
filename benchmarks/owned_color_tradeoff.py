"""Explore lab-only FIR cutoff and span tradeoffs; requires NumPy and GCC."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import tempfile
import time
import numpy as np
from owned_extended_audio import spectrum,db_ratio,ROOT

VARIANTS=((2,40,450),(4,40,450),(2,40,475),(4,40,475),(2,80,475),(4,80,475))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--old-adapter',type=Path,help='Optional previously compiled owned baseline for exact sample comparison');a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='skell-tradeoff-') as d:
        libpath=Path(d)/'variants.so'
        subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror',str(ROOT/'tests/fixtures/owned_color_tradeoff.cpp'),'-o',str(libpath)],check=True)
        lib=C.CDLL(str(libpath));fn=lib.render_variant
        ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS')
        fn.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];fn.restype=C.c_int
        old=None
        if a.old_adapter:
            oldlib=C.CDLL(str(a.old_adapter));old=oldlib.render_owned
            old.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint,C.c_uint];old.restype=C.c_int
        rows=[];timings=[];identity=[];delays=[]
        for fs in (44100,48000,96000):
            t=np.arange(fs+fs//4)/fs
            for hz in (7004,11004,17004,20004):
                for amp in (.1,.5,.9):
                    x=np.ascontiguousarray(np.column_stack((amp*np.sin(2*np.pi*hz*t),amp*.37*np.sin(2*np.pi*hz*t))))
                    out=np.empty_like(x);results=[]
                    for k,v in enumerate(VARIANTS):
                        if fn(k,fs,1,x,out,len(x))!=1 or not np.isfinite(out).all():raise RuntimeError('Render failed')
                        m=spectrum(out[-fs//4:,0],fs,hz);results.append(m)
                        if old is not None and k<2:
                            ref=np.empty_like(x)
                            if old(k+3,fs,1,x,ref,len(x),257)!=1 or not np.array_equal(ref,out):raise RuntimeError('Default output changed')
                            identity.append({'fs':fs,'hz':hz,'amp':amp,'factor':v[0],'max_abs_error':float(np.max(np.abs(ref-out)))})
                    for k in range(2,len(VARIANTS)):
                        ref=results[k%2]['fundamental_amplitude'];results[k]['fundamental_delta_vs_same_factor_default_db']=db_ratio(results[k]['fundamental_amplitude']**2,ref**2)
                    rows.append({'fs':fs,'hz':hz,'amp':amp,'results':results})
            x=np.zeros((256,2));x[0]=[1,.5];out=np.empty_like(x)
            for k,v in enumerate(VARIANTS):
                if fn(k,fs,0,x,out,len(x))!=1:raise RuntimeError('Impulse failed')
                expected=np.zeros_like(x);expected[v[1]]=x[0]
                if not np.array_equal(out,expected):raise RuntimeError('Dry delay mismatch')
                delays.append({'fs':fs,'variant':k,'dry_delay_samples':v[1]})
            t=np.arange(fs)/fs;sig=.3*np.sin(2*np.pi*997*t)+.1*np.sin(2*np.pi*7001*t);x=np.ascontiguousarray(np.column_stack((sig,.73*sig)));out=np.empty_like(x)
            for k,v in enumerate(VARIANTS):
                if fn(k,fs,1,x,out,fs)!=1:raise RuntimeError('Warmup failed')
                times=[]
                for _ in range(5):
                    start=time.perf_counter_ns();ok=fn(k,fs,1,x,out,fs);times.append((time.perf_counter_ns()-start)/1e6)
                    if ok!=1 or not np.isfinite(out).all():raise RuntimeError('Timing failed')
                timings.append({'fs':fs,'variant':k,'median_ms_per_audio_second':statistics.median(times),'raw_ms':times})
        result={'schema':1,'variants':VARIANTS,'rows':rows,'dry_delays':delays,'timings':timings,'baseline_exact_comparisons':identity,'native_sha256':hashlib.sha256(libpath.read_bytes()).hexdigest(),'old_adapter_sha256':hashlib.sha256(a.old_adapter.read_bytes()).hexdigest() if a.old_adapter else None,'limits':'Owned lab only; nonharmonic residual excludes harmonic-coincident aliases. Timing includes preparation and adapter. No vendor comparison or production selection.'}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('Completed',len(rows)*len(VARIANTS),'sweep renders;',len(identity),'exact default comparisons;',len(delays),'dry delay checks')

if __name__=='__main__':main()
