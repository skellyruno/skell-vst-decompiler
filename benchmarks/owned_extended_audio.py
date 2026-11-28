"""Repeatable owned saturation sweep and native render timing; no vendor execution.
Requires NumPy and the native compiler. Run from the repository root.
"""
import argparse
import ctypes as C
import hashlib
import json
import platform
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('presence', 'leveler', 'color', 'color_2x', 'color_4x')


def db_ratio(num, den):
    return float(10*np.log10(max(float(num), 1e-30)/max(float(den), 1e-30)))


def spectrum(x, fs, hz):
    """Coherent tone residual outside DC and integer in-band harmonics.
    Aliases coincident with harmonic bins are not measured by this metric.
    """
    n = len(x)
    k = round(hz*n/fs)
    if not 0 < k < n//2 or abs(hz*n/fs-k)>1e-8:
        raise ValueError('Requires a coherent tone below Nyquist')
    bins = np.abs(np.fft.rfft(x))**2
    bins[1:len(bins)-(n%2==0)] *= 2
    fund = bins[k]
    harmonics = np.arange(k, len(bins), k)
    total = bins.copy(); total[0] = 0; total[harmonics] = 0
    return {'nonharmonic_dbc': db_ratio(total.sum(), fund),
            'fundamental_amplitude': float(np.sqrt(2*fund)/n),
            'harmonic_distortion_dbc': db_ratio(bins[harmonics[1:]].sum(), fund)}


def run_sweep(work):
    library = work/'owned.so'
    subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror',
                    str(ROOT/'tests/fixtures/owned_audio_probe.cpp'),'-o',str(library)],check=True)
    lib=C.CDLL(str(library)); fn=lib.render_owned
    ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS')
    fn.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint,C.c_uint]; fn.restype=C.c_int
    def render(kind,fs,x,control=1,block=257):
        out=np.empty_like(x)
        if fn(kind,fs,control,x,out,len(x),block)!=1 or not np.isfinite(out).all():
            raise RuntimeError('Render failed')
        return out
    rows=[]; timings=[]
    for fs in (44100,48000,96000):
        # One second warm-up, one quarter second coherent measurement.
        n=fs+fs//4; t=np.arange(n)/fs
        for hz in (1000,3004,7004,11004,17004,20004):
            for amp in (.1,.5,.9):
                a=amp*np.sin(2*np.pi*hz*t)
                x=np.ascontiguousarray(np.column_stack((a,a)))
                engines={}
                for kind in (2,3,4):
                    out=render(kind,fs,x); tail=out[-fs//4:,0]
                    m=spectrum(tail,fs,hz)
                    m['peak']=float(np.max(np.abs(tail)))
                    engines[NAMES[kind]]=m
                for name in ('color_2x','color_4x'):
                    engines[name]['fundamental_delta_vs_1x_db']=db_ratio(engines[name]['fundamental_amplitude']**2,engines['color']['fundamental_amplitude']**2)
                rows.append({'fs':fs,'hz':hz,'input_peak':amp,'engines':engines})
        # Preallocated buffers; timing includes prepare and host adapter loop,
        # excludes Python array allocation and finite checking.
        t=np.arange(fs)/fs; a=.3*np.sin(2*np.pi*997*t)+.1*np.sin(2*np.pi*7001*t)
        x=np.ascontiguousarray(np.column_stack((a,.73*a))); out=np.empty_like(x)
        for kind,name in enumerate(NAMES):
            if fn(kind,fs,1,x,out,fs,256)!=1: raise RuntimeError('Warm-up failed')
            ts=[]
            for _ in range(5):
                start=time.perf_counter_ns(); result=fn(kind,fs,1,x,out,fs,256); elapsed=time.perf_counter_ns()-start
                if result!=1 or not np.isfinite(out).all(): raise RuntimeError('Timing render failed')
                ts.append(elapsed/1e6)
            timings.append({'fs':fs,'engine':name,'median_ms_per_audio_second':statistics.median(ts),'min_ms':min(ts),'max_ms':max(ts),'raw_ms':ts})
    return {'schema':1,'source_adapter_sha256':hashlib.sha256((ROOT/'tests/fixtures/owned_audio_probe.cpp').read_bytes()).hexdigest(),
            'native_binary_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),
            'environment':{'platform':platform.platform(),'machine':platform.machine(),'numpy':np.__version__,
                           'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0]},
            'rows':rows,'timings':timings,'limits':'Generated coherent tones, nonharmonic residual excludes harmonic-coincident aliases; no universal alias or audible quality claim. Timing includes preparation and adapter; not host CPU or plugin latency.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='skell-sweep-') as d:
        r=run_sweep(Path(d))
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print('Completed',len(r['rows'])*3,'tone renders and',len(r['timings'])*5,'timed runs')

if __name__=='__main__': main()
