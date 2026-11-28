"""Compare stereo detector descriptions on an independent fixture; no vendor loading."""
import argparse,ctypes,json,math
from pathlib import Path
import numpy as np
import pedalboard as pb
import soundfile as sf
from scipy.optimize import least_squares
from scipy.signal import resample_poly


def main():
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);p.add_argument('sources',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');lib=ctypes.CDLL(str(a.library.resolve()));fn=lib.stereo_detector;fn.argtypes=[ptr,ctypes.c_uint,ctypes.c_uint,ctypes.c_double,ptr,ptr,ptr];fn.restype=ctypes.c_int
    rng=np.random.default_rng(214);count=0
    def observe(x,fs,s):
        nonlocal count
        block=round(fs*.005);x=np.ascontiguousarray(x[:len(x)//block*block],dtype=np.float64);s=np.asarray(s,dtype=np.float64)
        y=pb.Compressor(**dict(zip(('threshold_db','ratio','attack_ms','release_ms'),s))).process(np.ascontiguousarray(x.T,dtype=np.float32),fs,buffer_size=128,reset=True).T.astype(float);count+=1
        u,v=(q.reshape(-1,block,2) for q in (x,y));energy=np.sum(u*u,axis=1);g=np.divide(np.sum(u*v,axis=1),energy,out=np.ones_like(energy),where=energy>1e-8);valid=(energy>1e-8)&(g>1e-6)
        return x,fs,s,block,20*np.log10(np.maximum(g,1e-6)),valid
    def synthetic(fs,k):
        t=np.arange(fs)/fs;env=rng.choice([.01,.04,.12,.3,.6,.8],(10,2));env=np.repeat(env,fs//10,axis=0);w=2*np.pi*(200+100*k)*t;z=np.column_stack((np.sin(w),np.sin(w*1.5+.3)));return env*z
    train_settings=[[-24,4,5,150],[-12,2,1,30],[-36,8,20,300],[-18,3,10,80],[-30,5,2,200],[-20,10,30,50]]
    test_settings=[[-27,6,7,110],[-15,2.5,15,240],[-32,3.5,3,65]]
    train=[observe(synthetic(48000,k),48000,s) for k,s in enumerate(train_settings)]
    validation=[observe(synthetic(48000,k+6),48000,s) for k,s in enumerate(test_settings)]
    def predict(row,m):
        x,fs,s,b,g,valid=row;out=np.empty_like(g);ok=fn(x,len(x),b,fs,s,np.ascontiguousarray(m,dtype=np.float64),out)
        if ok!=1:raise ValueError('native model rejected')
        return out
    def err(rows,m):return np.concatenate([(predict(r,m)-r[4])[r[5]] for r in rows])
    rms=lambda q:float(np.sqrt(np.mean(q*q)))
    models=[]
    for kind in ('linked','independent','partial'):
        def unpack(p):return np.r_[p,1. if kind=='linked' else 0.] if kind!='partial' else p
        start=[0.,1.,.16,.16]+([.25] if kind=='partial' else []);lo=[-10,.2,.01,.01]+([0.] if kind=='partial' else []);hi=[10,1.1,2,2]+([1.] if kind=='partial' else [])
        f=least_squares(lambda p:err(train,unpack(p)),start,bounds=(lo,hi),max_nfev=75)
        if not f.success:raise RuntimeError('fit did not converge')
        m=unpack(f.x);models.append(dict(model=kind,parameters=m.tolist(),training_rmse_db=rms(err(train,m)),validation_rmse_db=rms(err(validation,m))));print(models[-1],flush=True)
    selected=min(models,key=lambda m:m['validation_rmse_db'])['model']
    rows=[]
    for fs in (44100,48000,96000):
        for k,path in enumerate(a.sources):
            x,sr=sf.read(path,always_2d=True);x=x[:4*sr];x=np.repeat(x,2,axis=1) if x.shape[1]==1 else x;d=math.gcd(fs,sr);x=resample_poly(x,fs//d,sr//d,axis=0);r=observe(x,fs,test_settings[k%len(test_settings)])
            row=dict(rate=fs,source_index=k,settings=r[2].tolist(),errors={m['model']:rms(err([r],m['parameters'])) for m in models});rows.append(row);print(row,flush=True)
    result=dict(scope='independent Pedalboard fixture; training synthetic at 48k only, validation unseen synthetic settings, final withheld recordings at three rates',render_count=count,models=models,selected_by_validation=selected,final=rows)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
