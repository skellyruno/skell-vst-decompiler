"""Real mixed-music validation on private, fingerprinted files (not isolated stems)."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile
import numpy as np
import soundfile as sf
from scipy.signal import butter,sosfilt,resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();rows=[];seen=set()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'music.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_adaptive_native.cpp'),str(ROOT/'tests/fixtures/owned_bounded_peak.cpp'),str(ROOT/'tests/fixtures/owned_transition_peak.cpp'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS');f=dll.adaptive_native;b=dll.bounded_peak;c=dll.selective_color
        for g in (f,b):g.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];g.restype=C.c_int
        c.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];c.restype=C.c_int
        def render(fn,k,fs,x,param=None):
            y=np.empty_like(x);ok=fn(k,fs,x,y,len(x)) if param is None else fn(k,fs,param,x,y,len(x))
            if ok!=1 or not np.isfinite(y).all():raise RuntimeError('Render failed')
            return y
        for item in json.loads(a.manifest.read_text())['inputs']:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if fs!=48000 or x.shape[1]!=2 or len(x)<fs*60 or not np.isfinite(x).all():raise ValueError('Invalid 48k stereo input')
            # Predeclare three nonoverlapping ten-second excerpts at 1/4, 1/2, 3/4 duration.
            for frac in (.25,.5,.75):
                n=10*fs;start=round(frac*len(x))-n//2;v=np.ascontiguousarray(x[start:start+n]);entry={'id':item['id'],'sha256':digest,'start_frame':start,'frames':n,'fs':fs,'leveler':{}}
                for label,z in [('full',v),('lowpass_120hz',sosfilt(butter(4,120,fs=fs,output='sos'),v,axis=0)),('highpass_120hz',sosfilt(butter(4,120,fs=fs,btype='highpass',output='sos'),v,axis=0))]:
                    z=np.ascontiguousarray(z);ys=[render(f,k,fs,z,7.8280181884765625) for k in range(4)];base=ys[0];window=round(fs*.005);pk=np.max(np.abs(z.reshape(-1,window,2)),axis=(1,2));rise=np.diff(pk,prepend=0);mask=rise>=np.quantile(rise,.9);metrics=[]
                    for y in ys:
                        m=y*rms(base)/rms(y);mp=np.max(np.abs(m.reshape(-1,window,2)),axis=(1,2));metrics.append({'raw_gain_db':db(rms(y)/rms(z)),'raw_peak_dbfs':db(np.max(np.abs(y))),'matched_peak_dbfs':db(np.max(np.abs(m))),'matched_onset_peak_dbfs':db(np.sqrt(np.mean(mp[mask]**2))),'matched_difference_db':db(rms(m-base)/rms(base))})
                    entry['leveler'][label]=metrics
                colors=[render(c,k,fs,v) for k in range(4)];base=colors[1];bounded=render(b,2,fs,base,60);entry['color']=[{'sample_peak_dbfs':db(np.max(np.abs(y))),'estimated16_peak_dbfs':db(np.max(np.abs(resample_poly(y,16,1,axis=0,window=('kaiser',8.6))))),'raw_gain_db':db(rms(y)/rms(v))} for y in colors];entry['guard']={'gain_db':db(rms(bounded)/rms(base)),'sample_peak_dbfs':db(np.max(np.abs(bounded))),'estimated16_peak_dbfs':db(np.max(np.abs(resample_poly(bounded,16,1,axis=0,window=('kaiser',8.6)))))};rows.append(entry);print(item['id'],frac,flush=True)
    a.output.write_text(json.dumps({'schema':1,'rows':rows,'limits':'Three source MP3s, three excerpts per source; correlated within file. Filename-labeled instrumental beats, no human listening/stem confirmation. Diagnostic filtered copies are not isolated bass/drums. Equal measured attack at prior single step, RMS match, 5ms onset windows selected by top decile input peak rise. Estimated peaks not certified. No host or subjective result.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
