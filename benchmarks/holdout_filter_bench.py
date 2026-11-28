"""Frozen filter candidates, independent tone grid and recorded inputs."""
import argparse,json,math
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from benchmarks.short_filter_bench import design,process
from experiments.native_halfband import coefficients
from experiments.multirate_diagnostic import signature

def main():
    p=argparse.ArgumentParser();p.add_argument('sources',nargs=3);a=p.parse_args();b=coefficients(65,.3);filters=[(n,design(n,.49)[0],(n-1)//2+16) for n in (641,481,561)];rows=[];recorded=[]
    for fs in (44100,48000,96000):
        for ratio in (.165,.169,.201,.333,.485):
            hz=int(fs*ratio)+1
            for level in (.1,.85):
                x=level*np.sin(2*np.pi*hz*np.arange(2*fs+336)/fs);r=[]
                for n,h,d in filters:
                    y=process(x,h,b);r.append(dict(taps=n,**signature(y[fs+d:2*fs+d],fs,hz)))
                z=r[0]
                for v in r:
                    amp=20*np.log10(v['fundamental_peak']/z['fundamental_peak']);rows.append(dict(rate=fs,ratio=ratio,level=level,**v,amp_difference_db=float(amp),passed=bool(abs(amp)<=.1 and v['nonharmonic_db']<=max(-90,z['nonharmonic_db']+3))))
    for fs in (44100,48000,96000,192000):
        for i,path in enumerate(a.sources):
            x,sr=sf.read(path,always_2d=True);g=math.gcd(sr,fs);x=resample_poly(x[:sr,0],fs//g,sr//g);signals=[]
            for n,h,d in filters:signals.append(process(x,h,b)[d+800:len(x)-336+d-800])
            for (n,h,d),y in zip(filters,signals):recorded.append(dict(rate=fs,source=i,taps=n,relative_rms=float(np.linalg.norm(y-signals[0])/max(np.linalg.norm(signals[0]),1e-12))))
    summary=[]
    for n,_,d in filters:
        r=[x for x in rows if x['taps']==n];v=[x['relative_rms'] for x in recorded if x['taps']==n];summary.append(dict(taps=n,delay=d,passed=sum(x['passed'] for x in r),worst_nonharmonic_db=max(x['nonharmonic_db'] for x in r),max_amplitude_delta_db=max(abs(x['amp_difference_db']) for x in r),max_recorded_relative_rms=max(v)))
    print(summary,flush=True);Path('holdout_filter_results.json').write_text(json.dumps(dict(renders=len(rows)+len(recorded),summary=summary,tones=rows,recorded=recorded),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
