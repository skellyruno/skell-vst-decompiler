"""Measure independent lab engines on explicitly selected local vocal files.
Input manifest: {"inputs":[{"id":"private-id","stage":"dry or processed label",
"path":"/local/file.wav","sha256":"exact file digest"}, ...]}.
Private report/listening files stay local; do not commit them or the manifest.
Requires NumPy, SciPy, SoundFile and GCC. No vendor executable is loaded.
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
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = [('presence',0,0),('leveler',1,0),('color_1x',2,0),
           ('color_2x',3,40),('color_4x',4,40),('color_2x_wide40',2,40),
           ('color_4x_wide40',3,40),('color_2x_wide80',4,80),('color_4x_wide80',5,80)]
BANDS = [(80,250),(250,1000),(1000,4000),(4000,8000),(8000,16000),(16000,20000)]


def rms(x): return float(np.sqrt(np.mean(np.square(x))))
def db(x): return float(20*np.log10(max(float(x),1e-15)))
def estimate_peak(x): return float(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))))
def match(x,ref):
    a,b=rms(x),rms(ref)
    if a<=1e-12 or b<=1e-12: raise ValueError('Silent comparison')
    return x*(b/a)


def band_db(x,fs):
    n=min(4096,len(x)); f,p=signal.welch(x,fs=fs,nperseg=n,axis=0)
    return [float(10*np.log10(max(np.sum(p[(f>=lo)&(f<min(hi,fs/2))]),1e-30))) if np.any((f>=lo)&(f<min(hi,fs/2))) else None for lo,hi in BANDS]


def compare(x,y,fs):
    """Same input-length, delay-aligned, unnormalized signals; no alias claim."""
    matched=match(y,x); xp=estimate_peak(x); yp=estimate_peak(y); mp=estimate_peak(matched)
    a,b=band_db(x,fs),band_db(matched,fs)
    return {'raw_gain_db':db(rms(y)/rms(x)),'input_peak_est_dbfs':db(xp),'output_peak_est_dbfs':db(yp),
            'matched_peak_est_dbfs':db(mp),'matched_peak_delta_db':db(mp/xp),
            'matched_null_db':db(rms(matched-x)/rms(x)),
            'matched_band_delta_db':[v-u if v is not None and u is not None else None for u,v in zip(a,b)],
            'raw_samples_over_full_scale':int(np.count_nonzero(np.abs(y)>1)),
            'input_crest_db':db(np.max(np.abs(x))/rms(x)),'output_crest_db':db(np.max(np.abs(y))/rms(y))}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--listen-dir',type=Path);p.add_argument('--listen-id',action='append',default=[]);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());rows=[];seen=set()
    with tempfile.TemporaryDirectory(prefix='skell-vocals-') as d:
        libs=[]
        for name in ('owned_audio_probe','owned_color_tradeoff'):
            path=Path(d)/(name+'.so');subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror',str(ROOT/'tests/fixtures'/ (name+'.cpp')),'-o',str(path)],check=True);libs.append(C.CDLL(str(path)))
        ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS');fn=libs[0].render_owned;fv=libs[1].render_variant
        fn.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint,C.c_uint];fn.restype=C.c_int
        fv.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];fv.restype=C.c_int
        for item in manifest['inputs']:
            path=Path(item['path']);digest=hashlib.sha256(path.read_bytes()).hexdigest()
            if digest!=item['sha256']:raise ValueError('Input fingerprint mismatch')
            x,fs=sf.read(path,dtype='float64',always_2d=True)
            if x.shape[1] not in (1,2) or not 8000<=fs<=384000 or not np.isfinite(x).all() or not len(x):raise ValueError('Unsupported input')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            x=np.ascontiguousarray(x);key=hashlib.sha256(x.tobytes()+str(fs).encode()).hexdigest()
            if key in seen:raise ValueError('Duplicate decoded input')
            seen.add(key);outputs={};metrics={}
            for i,(name,kind,delay) in enumerate(CONFIGS):
                # Flush enough samples for alignment, not reverb/tail evaluation.
                source=np.ascontiguousarray(np.pad(x,((0,delay),(0,0))));y=np.empty_like(source)
                def render(out,wet,block):
                    return fn(kind,fs,wet,source,out,len(source),block) if i<5 else fv(kind,fs,wet,source,out,len(source))
                times=[]
                for _ in range(3):
                    start=time.perf_counter_ns();ok=render(y,1,257);times.append((time.perf_counter_ns()-start)/1e6)
                    if ok!=1 or not np.isfinite(y).all():raise RuntimeError('Render failed')
                aligned=y[delay:delay+len(x)].copy();z=np.empty_like(source)
                if render(z,0,257)!=1 or not np.array_equal(z[delay:delay+len(x)],x):raise RuntimeError('Dry identity failed')
                if i<5:
                    if render(z,1,64)!=1 or not np.array_equal(y,z):raise RuntimeError('Block partition changed output')
                metrics[name]=compare(x,aligned,fs);metrics[name].update(delay_samples=delay,dry_exact=True,partition_exact=(True if i<5 else None),median_ms_per_audio_second=statistics.median(times)/(len(x)/fs))
                outputs[name]=aligned
            # Difference to 4x default is a relative consistency metric only.
            for name in outputs:
                if name.startswith('color'):
                    ref=outputs['color_4x'];metrics[name]['matched_difference_vs_default_4x_db']=db(rms(match(outputs[name],ref)-ref)/rms(ref))
            row={'id':item['id'],'stage':item['stage'],'source_sha256':digest,'fs':fs,'frames':len(x),'seconds':len(x)/fs,'metrics':metrics};rows.append(row)
            if a.listen_dir and item['id'] in a.listen_id:
                if Path(item['id']).name!=item['id']:raise ValueError('Invalid listening id')
                folder=a.listen_dir/item['id'];folder.mkdir(parents=True,exist_ok=True)
                listen={'original':x,**{k:match(v,x) for k,v in outputs.items()}}; common=min(1.,10**(-1/20)/max(estimate_peak(v) for v in listen.values()))
                for k,v in listen.items():sf.write(folder/(k+'.flac'),v*common,fs,subtype='PCM_24')
                row['listening_common_gain_db']=db(common)
            print(item['id'],len(x),fs,flush=True)
    report={'schema':1,'inputs':rows,'bands_hz':BANDS,'configs':CONFIGS,'timing_repeats':3,'limits':'Local private excerpts, not independent performances necessarily; native lab engines only. Estimated intersample peak via 4x SciPy polyphase interpolation, not certified true peak. RMS-matched spectral and null differences are not alias measures or vendor equivalence. Timing includes preparation and adapter; no host validation.'}
    a.output.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
