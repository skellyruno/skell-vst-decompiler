"""Compare one/two-stage descriptions on independent built-in fixtures."""
import argparse,ctypes,json,math
from pathlib import Path
import numpy as np
import pedalboard as pb
import soundfile as sf
from scipy.optimize import least_squares
from scipy.signal import resample_poly

def main():
    a=argparse.ArgumentParser();a.add_argument('library');a.add_argument('sources',nargs='+');a.add_argument('--output',required=True);a=a.parse_args()
    ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');fn=ctypes.CDLL(str(Path(a.library).resolve())).cascade_id;fn.argtypes=[ptr,ptr,ctypes.c_uint,ctypes.c_double,ptr,ctypes.c_int];fn.restype=ctypes.c_int
    rng=np.random.default_rng(511);count=0
    def observe(x,fs,kind):
        nonlocal count
        x=np.ascontiguousarray(x,dtype=np.float64);fx=[pb.Compressor(threshold_db=-19,ratio=3,attack_ms=2,release_ms=160)]
        if kind=='cascade':fx.append(pb.Compressor(threshold_db=-24,ratio=4,attack_ms=24,release_ms=600))
        y=pb.Pedalboard(fx).process(x.astype(np.float32)[None,:],fs,buffer_size=128,reset=True)[0].astype(float);count+=1
        return x,y,fs
    def signal(fs,k):
        t=np.arange(fs)/fs;env=np.repeat(rng.choice([.015,.04,.08,.17,.4,.75,.9],10),fs//10);return env*(np.sin(2*np.pi*(119+83*k)*t)+.21*np.sin(2*np.pi*(233+19*k)*t))/1.21
    def predict(row,p):
        x,y,fs=row;out=np.empty_like(x);assert fn(x,out,len(x),fs,np.ascontiguousarray(p),len(p)//4)==1;return out
    rms=lambda x:float(np.sqrt(np.mean(x*x)))
    def error(rows,p):return np.concatenate([(predict(r,p)-r[1])[::8] for r in rows])
    result=[]
    for kind in ('single','cascade'):
        train=[observe(signal(48000,k),48000,kind) for k in range(3)];valid=[observe(signal(fs,k+3),fs,kind) for k,fs in enumerate((44100,96000))];models=[]
        for stages in (1,2):
            start=[-21,.6,.002,.05] if stages==1 else [-18,.6,.001,.03,-24,.6,.006,.1];lo=[-60,0,.00005,.00005]*stages;hi=[-1,1,.2,2]*stages
            f=least_squares(lambda p:error(train,p),start,bounds=(lo,hi),max_nfev=100)
            row=dict(stages=stages,parameters=f.x.tolist(),converged=bool(f.success),evaluations=f.nfev,train_rms=rms(error(train,f.x)),validation_rms=rms(error(valid,f.x)));models.append(row);print(kind,row,flush=True)
        best=min(m['validation_rms'] for m in models);selected=next(m for m in models if m['validation_rms']<=max(1e-6,best*1.05));hold=[]
        for fs in (44100,48000,96000,192000):
            for k,path in enumerate(a.sources):
                x,sr=sf.read(path,always_2d=True);x=x[:4*sr,0];d=math.gcd(fs,sr);x=resample_poly(x,fs//d,sr//d);row=observe(x,fs,kind);hold.append(dict(rate=fs,source=k,relative_rms={str(m['stages']):rms(predict(row,m['parameters'])-row[1])/max(rms(row[1]),1e-12) for m in models}))
        result.append(dict(fixture=kind,models=models,selected=selected['stages'],holdout=hold))
    Path(a.output).write_text(json.dumps(dict(scope='independent built-in fixture chains, fixed settings, no commercial plugin',renders=count,results=result),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
