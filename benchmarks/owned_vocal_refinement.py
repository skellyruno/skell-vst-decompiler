"""Local private vocal benchmark; never upload manifest, audio, or row data.
Run with explicit fingerprinted manifest, --start/--count for bounded batches.
Uses owned native adapters only; not a plugin-host or vendor equivalence test.
"""
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
import soundfile as sf
if __package__:
    from .owned_private_vocal import ROOT, db, rms, estimate_peak
else:
    from owned_private_vocal import ROOT, db, rms, estimate_peak


def renderer(work):
    libpath=Path(work)/'refinement.so'
    subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror',str(ROOT/'tests/fixtures/owned_vocal_refinement.cpp'),'-o',str(libpath)],check=True)
    lib=C.CDLL(str(libpath));fn=lib.render_refinement
    ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS')
    fn.argtypes=[C.c_int,C.c_double,C.c_double,C.c_double,ptr,ptr,C.c_uint];fn.restype=C.c_int
    def render(kind,fs,wet,trim,x,out):
        start=time.perf_counter_ns();ok=fn(kind,fs,wet,trim,x,out,len(x));elapsed=(time.perf_counter_ns()-start)/1e6
        if ok!=1 or not np.isfinite(out).all():raise RuntimeError('Native render failed')
        return elapsed
    return render,hashlib.sha256(libpath.read_bytes()).hexdigest()


def maximum_error(a,b):return float(np.max(np.abs(a-b)))
def require_equal(a,b):
    err=maximum_error(a,b)
    if err>1e-12:raise RuntimeError('Waveform parity failed')
    return err


def presence_checks(render,x,fs):
    baseline=np.empty_like(x);out=np.empty_like(x);full=np.empty_like(x)
    render(0,fs,1,0,x,baseline);render(1,fs,1,-4,x,full)
    full_err=require_equal(full,baseline*10**(-4/20));rows=[]
    for wet in (0,.5,1):
        render(0,fs,wet,0,x,baseline);render(1,fs,wet,0,x,out);parity=require_equal(baseline,out)
        render(1,fs,wet,-4,x,out);blend=require_equal(out,x*(1-wet)+full*wet)
        rows.append({'wet':wet,'zero_trim_parity_max_error':parity,'wet_only_blend_max_error':blend,
                     'baseline_peak_est_dbfs':db(estimate_peak(baseline)),'trimmed_peak_est_dbfs':db(estimate_peak(out)),
                     'trimmed_overload_samples':int(np.count_nonzero(np.abs(out)>1)),
                     'trimmed_raw_gain_db':db(rms(out)/rms(x))})
    return {'full_wet_scale_error':full_err,'mix_cases':rows}


def color_checks(render,x,fs):
    inp=np.ascontiguousarray(np.pad(x,((0,40),(0,0))));base=np.empty_like(inp);fast=np.empty_like(inp)
    rows=[]
    for factor,k in ((2,2),(4,4)):
        cases=[]
        for wet,trim in ((1,0),(.5,-12),(0,-12)):
            render(k,fs,wet,trim,inp,base);render(k+1,fs,wet,trim,inp,fast)
            err=require_equal(base,fast)
            if wet==0 and not np.array_equal(fast[40:40+len(x)],x):raise RuntimeError('Dry alignment failed')
            cases.append({'wet':wet,'trim_db':trim,'max_error':err,'exact':bool(np.array_equal(base,fast))})
        base_ms=[];fast_ms=[]
        for i in range(3):
            if i%2:
                fast_ms.append(render(k+1,fs,1,0,inp,fast));base_ms.append(render(k,fs,1,0,inp,base))
            else:
                base_ms.append(render(k,fs,1,0,inp,base));fast_ms.append(render(k+1,fs,1,0,inp,fast))
            require_equal(base,fast)
        seconds=len(x)/fs
        rows.append({'factor':factor,'cases':cases,'baseline_ms_per_second':statistics.median(base_ms)/seconds,
                     'contiguous_ms_per_second':statistics.median(fast_ms)/seconds,'baseline_raw_ms':base_ms,'contiguous_raw_ms':fast_ms})
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text())['inputs']
    if a.start<0 or a.count<1 or a.start>=len(manifest):raise ValueError('Invalid batch')
    rows=[];seen=set()
    with tempfile.TemporaryDirectory(prefix='skell-vocal-refine-') as d:
        render,sha=renderer(d)
        for item in manifest[a.start:a.start+a.count]:
            path=Path(item['path']);digest=hashlib.sha256(path.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(path,dtype='float64',always_2d=True)
            if x.shape[1] not in (1,2) or not len(x) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid audio')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            x=np.ascontiguousarray(x)
            rows.append({'id':item['id'],'stage':item['stage'],'source_sha256':digest,'fs':fs,'seconds':len(x)/fs,
                         'presence':presence_checks(render,x,fs),'color':color_checks(render,x,fs)})
            print(item['id'],flush=True)
    a.output.write_text(json.dumps({'schema':1,'native_sha256':sha,'inputs':rows,'limits':'Local real vocal excerpt comparisons, fixed trims, no production selection. Estimated peak not certified true peak. Wall time includes prepare and native loop, not host CPU.'},indent=2)+'\n')

if __name__=='__main__':main()
