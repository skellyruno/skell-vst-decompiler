"""Score already selected model with no fitting, fresh histories and host blocks."""
import argparse,ctypes,json
from pathlib import Path
import numpy as np
import pedalboard as pb

def main():
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);p.add_argument('fit',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    fit=json.loads(a.fit.read_text());m=np.ascontiguousarray(next(r['parameters'] for r in fit['models'] if r['model']==fit['selected_by_validation']),dtype=np.float64)
    ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');lib=ctypes.CDLL(str(a.library.resolve()));fn=lib.stereo_detector_waveform;fn.argtypes=[ptr,ctypes.c_uint,ctypes.c_double,ptr,ptr,ptr];fn.restype=ctypes.c_int
    rows=[];rng=np.random.default_rng(918);count=0
    for fs in (44100,48000,96000,192000):
        t=np.arange(10*fs)/fs
        # Each history is 10 s, distinct and asymmetric, alternating bursts, long silence, quiet suffix.
        for k,s in enumerate(([-34,12,.8,900],[-9,1.8,40,450],[-22,5,12,1500])):
            a1=np.repeat([.7,.02,.5,0,.01,.8,0,.03,.4,.02],fs);a2=np.repeat([.02,.6,.01,.3,0,.015,.7,.04,.02,.1],fs)
            x=np.ascontiguousarray(np.column_stack((a1*(np.sin(2*np.pi*(137+101*k)*t)+.1*rng.uniform(-1,1,len(t)))/1.1,a2*np.sin(2*np.pi*(233+133*k)*t+.3))),dtype=np.float32)
            v=np.ascontiguousarray(x,dtype=np.float64);pred=np.empty_like(v);s=np.ascontiguousarray(s,dtype=np.float64)
            assert fn(v,len(v),fs,s,m,pred)==1
            baseline=None
            for b in (64,128,512,1024):
                y=pb.Compressor(**dict(zip(('threshold_db','ratio','attack_ms','release_ms'),s))).process(np.ascontiguousarray(x.T),fs,buffer_size=b,reset=True).T;count+=1
                if baseline is None:baseline=y.copy()
                err=pred-y
                row=dict(rate=fs,block=b,settings=s.tolist(),seconds=10,relative_rms=float(np.linalg.norm(err)/np.linalg.norm(y)),peak_absolute=float(np.max(abs(err))),block_max_difference=float(np.max(abs(y-baseline))))
                rows.append(row)
            print(fs,k,rows[-1],flush=True)
    a.output.write_text(json.dumps(dict(scope='independent fixture; no fit, fresh histories, unseen settings',renders=count,results=rows),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
