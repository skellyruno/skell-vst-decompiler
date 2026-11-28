"""Compare shorter causal symmetric halfband designs offline."""
import json,time
from pathlib import Path
import numpy as np
from scipy.signal import remez,upfirdn,freqz
from experiments.native_halfband import coefficients
from experiments.multirate_diagnostic import signature

def design(n,edge):
    h=remez(n,[0,edge,1-edge,1],[1,0],fs=2,maxiter=100,grid_density=32)
    h=(h+h[::-1])*.5;h[::2]=0.;h[n//2]=.5
    f,v=freqz(h,worN=65536,fs=2);a=abs(v)
    return h,dict(stop_db=float(20*np.log10(a[f>=1-edge].max())),ripple_db=float(20*np.log10(a[f<=edge].max()/a[f<=edge].min())))

def process(x,a,b):
    u=upfirdn(2*a,x,up=2)[:2*len(x)];v=upfirdn(2*b,u,up=2)[:4*len(x)]
    w=upfirdn(b,np.tanh(4*v),down=2)[:2*len(x)];return upfirdn(a,w,down=2)[:len(x)]

def main():
    specs=[(641,.49),(321,.48),(161,.46),(81,.42),(161,.48),(321,.49)]
    b=coefficients(65,.3);models=[];rows=[]
    for n,e in specs:
        a,info=design(n,e);delay=(n-1)//2+16
        models.append(dict(taps=n,edge=e,delay=delay,**info))
        for fs in (44100,48000,96000):
            for ratio in (.17,.211,.31,.45,.49):
                hz=int(fs*ratio)+1;t=np.arange(2*fs+delay)/fs
                for level in (.02,.7):
                    x=level*np.sin(2*np.pi*hz*t);start=time.perf_counter();y=process(x,a,b);elapsed=time.perf_counter()-start
                    rows.append(dict(taps=n,edge=e,rate=fs,ratio=ratio,level=level,seconds=elapsed,**signature(y[fs+delay:2*fs+delay],fs,hz)))
        print(models[-1],flush=True)
    base=rows[:30];summary=[]
    for j,m in enumerate(models):
        v=rows[j*30:(j+1)*30];d=np.array([x['nonharmonic_db']-z['nonharmonic_db'] for x,z in zip(v,base)]);amp=np.array([20*np.log10(x['fundamental_peak']/z['fundamental_peak']) for x,z in zip(v,base)]);tm=np.array([x['seconds']/z['seconds'] for x,z in zip(v,base)])
        passed=[bool((x['nonharmonic_db']<=max(-90,z['nonharmonic_db']+3)) and abs(a)<=.1) for x,z,a in zip(v,base,amp)]
        r=dict(**m,passed=sum(passed),worst_nonharmonic_db=max(x['nonharmonic_db'] for x in v),max_fundamental_difference_db=float(max(abs(amp))),median_time_ratio=float(np.median(tm)),max_spectral_regression_db=float(max(d)))
        summary.append(r);print(r,flush=True)
    Path('short_filter_results.json').write_text(json.dumps(dict(scope='original causal offline FIR experiments, not host latency measurements',renders=len(rows),summary=summary,results=rows),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
