"""Explore unequal interpolation and decimation designs with explicit latency."""
import json,time
from pathlib import Path
import numpy as np
from scipy.signal import remez,upfirdn
from experiments.native_halfband import coefficients
from experiments.multirate_diagnostic import signature
from benchmarks.short_filter_bench import design

def render(x,a,c,b):
    u=upfirdn(2*a,x,up=2)[:2*len(x)];v=upfirdn(2*b,u,up=2)[:4*len(x)];w=upfirdn(b,np.tanh(4*v),down=2)[:2*len(x)];return upfirdn(c,w,down=2)[:len(x)]

def main():
    b=coefficients(65,.3);ref=design(641,.49)[0];configs=[(321,481,.49,.505,2),(321,481,.49,.505,10),(321,561,.49,.505,4),(401,481,.49,.507,10)]
    models=[]
    for ni,no,pe,se,weight in configs:
        a=design(ni,.49)[0];c=remez(no,[0,pe,se,1],[1,0],weight=[1,weight],fs=2,maxiter=100,grid_density=32);delay=(ni+no-2)//4+16;models.append((ni,no,pe,se,weight,a,c,delay))
    # This grid was informed by prior failed holds; it is development, not a final holdout.
    rows=[]
    for fs in (44100,48000,96000):
        for ratio in (.169,.17,.211,.31,.485,.49):
            hz=int(fs*ratio)+1;t=np.arange(2*fs+336)/fs
            for lev in (.1,.7):
                x=lev*np.sin(2*np.pi*hz*t);y=render(x,ref,ref,b);z=signature(y[fs+336:2*fs+336],fs,hz)
                for ni,no,pe,se,w,a,c,d in models:
                    start=time.perf_counter();y=render(x,a,c,b);elapsed=time.perf_counter()-start;v=signature(y[fs+d:2*fs+d],fs,hz);amp=float(20*np.log10(v['fundamental_peak']/z['fundamental_peak']));rows.append(dict(interp=ni,decim=no,pass_edge=pe,stop_edge=se,weight=w,latency=d,rate=fs,ratio=ratio,level=lev,seconds=elapsed,**v,amp_delta_db=amp,baseline_nonharmonic_db=z['nonharmonic_db'],passed=bool(abs(amp)<=.1 and v['nonharmonic_db']<=max(-90,z['nonharmonic_db']+3))))
    summary=[]
    for ni,no,pe,se,w,a,c,d in models:
        r=[z for z in rows if (z['interp'],z['decim'],z['weight'])==(ni,no,w)];summary.append(dict(interp=ni,decim=no,weight=w,latency=d,passed=sum(z['passed'] for z in r),total=len(r),max_amp_delta=max(abs(z['amp_delta_db']) for z in r),worst_nonharmonic=max(z['nonharmonic_db'] for z in r)))
    print(summary,flush=True);Path('asymmetric_filter_results.json').write_text(json.dumps(dict(scope='development grid includes prior failure points, not final holdout',renders=len(rows)+len(rows)//len(models),summary=summary,results=rows),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
