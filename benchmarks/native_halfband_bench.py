"""Causal projected halfband parity and timing against matched dense native reference."""
import argparse,json,math,time
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly,freqz
from experiments.native_halfband import coefficients,load_native,causal_oracle,LATENCY
from experiments.multirate_diagnostic import signature,color

def main():
    p=argparse.ArgumentParser();p.add_argument('library');p.add_argument('sources',nargs=3,type=Path);p.add_argument('--output',required=True);a=p.parse_args();run=load_native(a.library);rows=[];recorded=[];spectral=[];rng=np.random.default_rng(114);count=0
    def rel(a,b):return float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-12))
    def paired(x):
        nonlocal count
        # Alternate order to reduce warmup bias. Preparation and validation included.
        times=[[],[]];out=[None,None]
        for j in range(3):
            for k in ((0,1) if j%2==0 else (1,0)):
                t=time.perf_counter();out[k]=run(x,symmetric=bool(k));times[k].append(time.perf_counter()-t);count+=1
        return out,[float(np.median(t)) for t in times]
    for fs in (44100,48000,96000,192000):
        for label,x in [('impulse',np.r_[.5,np.zeros(fs//10-1)]),('noise',rng.uniform(-.8,.8,fs//10)),('silence',np.zeros(fs//10))]:
            a1=run(x,symmetric=False);b1=run(x);q=causal_oracle(x);count+=2;rows.append(dict(rate=fs,signal=label,oracle_max=float(np.max(abs(b1-q))),dense_max=float(np.max(abs(b1-a1)))))
        for i,path in enumerate(a.sources):
            x,sr=sf.read(path,always_2d=True);g=math.gcd(sr,fs);x=resample_poly(x[:sr,0],fs//g,sr//g);out,times=paired(x);q=causal_oracle(x);ref=color(x,4,span=200);z=out[1][LATENCY:];base=ref[:-LATENCY];guard=800;recorded.append(dict(rate=fs,source=i,timing_dense=times[0],timing_symmetric=times[1],oracle_max=float(np.max(abs(q-out[1]))),dense_max=float(np.max(abs(out[0]-out[1]))),relative_to_long_offline=rel(z[guard:-guard],base[guard:-guard])))
        print(fs,'causal tests done',flush=True)
        if fs==192000:continue
        for ratio in (.17,.211,.31,.45,.49):
            hz=int(fs*ratio)+1;t=np.arange(fs*3+LATENCY)/fs
            for level in (.02,.7):
                x=level*np.sin(2*np.pi*hz*t);y=run(x);count+=1;v=y[fs+LATENCY:2*fs+LATENCY];spectral.append(dict(rate=fs,ratio=ratio,hz=hz,level=level,**signature(v,fs,hz)))
    Path(a.output).write_text(json.dumps(dict(scope='original projected halfband native offline experiment',latency_samples=LATENCY,native_calls=count,known=rows,recorded=recorded,spectral=spectral),indent=2,allow_nan=False)+'\n')
    print('native calls',count,'known max',max(max(x['oracle_max'],x['dense_max']) for x in rows),'recorded max',max(max(x['oracle_max'],x['dense_max']) for x in recorded),'ratio',np.median([x['timing_symmetric']/x['timing_dense'] for x in recorded]),'offline relative max',max(x['relative_to_long_offline'] for x in recorded),flush=True)
if __name__=='__main__':main()
