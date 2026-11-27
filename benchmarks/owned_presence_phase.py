"""Owned presence topology benchmark; private audio and per-input rows stay local."""
import argparse, ctypes as C, hashlib, json, pathlib, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy.signal import welch
ROOT=pathlib.Path(__file__).resolve().parents[1]
BANDS=((80,250),(250,1000),(1000,4000),(4000,8000),(8000,16000))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def levels(x,fs):
    f,p=welch(x,fs=fs,nperseg=min(4096,len(x)),axis=0)
    return [db(np.sqrt(p[(f>=lo)&(f<hi)].sum())) for lo,hi in BANDS]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'phase.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_presence_phase.cpp'),'-o',str(lib)],check=True)
        f=C.CDLL(str(lib)).presence_phase;ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS');f.argtypes=[C.c_int,C.c_double,C.c_double,C.c_double,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int
        def render(k,fs,boost,amount,wet,x):
            y=np.empty_like(x)
            if f(k,fs,boost,amount,wet,x,y,len(x))!=1 or not np.isfinite(y).all():raise RuntimeError('Render failed')
            return y
        tones=[];rows=[];seen=set()
        for fs in (44100,48000,96000):
            t=np.arange(fs)/fs
            for hz in (100,500,1000,2000,2600,3200,5000,9000,15000):
                x=np.ascontiguousarray(np.column_stack((.01*np.sin(2*np.pi*hz*t),.007*np.sin(2*np.pi*hz*t))))
                for boost in (0,3):
                    for wet in (.5,1):
                        a0,a1=[render(k,fs,boost,0,wet,x) for k in (0,1)]
                        if boost==0 and not np.array_equal(a1,x):raise RuntimeError('Neutral identity')
                        tones.append({'fs':fs,'hz':hz,'boost':boost,'wet':wet,'gain_db':[db(rms(y[fs//2:])/rms(x[fs//2:])) for y in (a0,a1)]})
        for item in json.loads(a.manifest.read_text())['inputs']:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if x.shape[1] not in (1,2) or not len(x) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid input')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            x=np.ascontiguousarray(x);cases=[];original=np.array(levels(x,fs))
            for boost,amount,wet in ((0,0,.5),(0,0,1),(3,.7,.5),(3,.7,1)):
                ys=[render(k,fs,boost,amount,wet,x) for k in (0,1)]
                if boost==0 and not np.array_equal(ys[1],x):raise RuntimeError('Neutral vocal mismatch')
                band_delta=[(np.array(levels(y*rms(x)/rms(y),fs))-original).tolist() for y in ys]
                cases.append({'boost':boost,'amount':amount,'wet':wet,'gain_db':[db(rms(y)/rms(x)) for y in ys],'difference_from_dry_db':[db(rms(y-x)/rms(x)) for y in ys],'peak_dbfs':[db(np.max(np.abs(y))) for y in ys],'over_scale_samples':[int(np.count_nonzero(np.abs(y)>1)) for y in ys],'matched_band_delta_db':band_delta})
            rows.append({'id':item['id'],'stage':item['stage'],'fs':fs,'cases':cases})
        a.output.write_text(json.dumps({'schema':1,'bands_hz':BANDS,'tone_rows':tones,'vocal_rows':rows,'limits':'Independent topology comparison. Neutral is boost=0 and amount=0, not all default settings. Peak is sample peak; no listening, host or vendor equivalence.'},indent=2)+'\n')
if __name__=='__main__':main()
