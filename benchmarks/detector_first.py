"""Compare sample-rate detector-first descriptions vs block-rate baseline on withheld sources."""
import argparse, ctypes, json, math
from pathlib import Path
import numpy as np
import soundfile as sf
import pedalboard as pb
from scipy.optimize import least_squares
from scipy.signal import resample_poly
from skell_vst_decompiler.adaptive_behavior import envelope_features,predict

def main():
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);p.add_argument('sources',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    lib=ctypes.CDLL(str(a.library.resolve()));fn=lib.predict_detector
    ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');fn.argtypes=[ptr,ctypes.c_uint,ctypes.c_uint,ctypes.c_double,ptr,ctypes.c_int,ptr];fn.restype=None
    rng=np.random.default_rng(719);results=[];renders=0
    for fs in (44100,48000,96000):
        block=round(fs*.005);train=[];hold=[]
        def observe(x):
            nonlocal renders
            x=np.ascontiguousarray(x,dtype=np.float64);x=x[:len(x)//block*block];y=pb.Compressor(threshold_db=-24,ratio=4,attack_ms=5,release_ms=150).process(np.ascontiguousarray(x.T,dtype=np.float32),fs,buffer_size=128,reset=True).T;renders+=1
            return x,envelope_features(x,y,fs)
        # Vary carrier, asymmetry, crest factor and event durations without human recordings.
        for k in range(5):
            t=np.arange(2*fs)/fs;env=np.repeat(rng.choice([.01,.04,.1,.2,.45,.65],20),fs//10);env=np.pad(env,(0,len(t)-len(env)),mode='edge');w=2*np.pi*(125+100*k)*t
            s=(np.sin(w)+.3*np.sin(2*w+.8*k)+.15*np.sin(3*w))/(1.45);s=s if k<4 else rng.uniform(-1,1,len(t));x=np.column_stack((env*s,env*.7*np.roll(s,3*k)));train.append(observe(x))
        for path in a.sources:
            x,sr=sf.read(path,always_2d=True);x=x[:6*sr];x=np.repeat(x,2,axis=1) if x.shape[1]==1 else x;d=math.gcd(fs,sr);hold.append(observe(resample_poly(x,fs//d,sr//d,axis=0)))
        def prediction(row,p,kind):
            x,r=row
            if kind=='block':return predict(r['peak'],r['dt'],p,'single')
            out=np.empty(len(x)//block);fn(x,len(x),block,fs,np.ascontiguousarray(p,dtype=np.float64),int(kind=='power'),out);return out
        def err(rows,p,kind):return np.concatenate([(prediction(row,p,kind)-row[1]['gain_db'])[row[1]['valid']] for row in rows])
        def rmse(z):return float(np.sqrt(np.mean(z*z)))
        out=[]
        for kind in ('block','amplitude','power'):
            fit=least_squares(lambda p:err(train,p,kind),[-24,.75,.005,.15],bounds=([-60,0,.0002,.002],[-1,1,.2,2]),max_nfev=80)
            if not fit.success:raise RuntimeError('fit failed')
            out.append(dict(model=kind,train_rmse_db=rmse(err(train,fit.x,kind)),holdout_rmse_db=rmse(err(hold,fit.x,kind)),per_source=[rmse(err([r],fit.x,kind)) for r in hold],parameters=fit.x.tolist()))
        results.append(dict(rate=fs,models=out));print(fs,out,flush=True)
    a.output.write_text(json.dumps(dict(scope='independent fixture; three reused sources plus new archived narration; synthetic training',renders=renders,results=results),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
