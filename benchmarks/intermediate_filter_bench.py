"""Narrower latency alternatives, same preregistered comparison grid."""
import json,time
from pathlib import Path
import numpy as np
from benchmarks.short_filter_bench import design,process
from experiments.native_halfband import coefficients
from experiments.multirate_diagnostic import signature

def main():
    base=json.loads(Path('short_filter_results.json').read_text())['results'][:30];b=coefficients(65,.3);rows=[];summary=[]
    for n,e in ((401,.49),(481,.49),(561,.49),(481,.488)):
        a,m=design(n,e);delay=(n-1)//2+16;results=[]
        for z in base:
            fs=z['rate'];hz=int(fs*z['ratio'])+1;t=np.arange(2*fs+delay)/fs;x=z['level']*np.sin(2*np.pi*hz*t);start=time.perf_counter();y=process(x,a,b);elapsed=time.perf_counter()-start
            r=dict(taps=n,edge=e,rate=fs,ratio=z['ratio'],level=z['level'],seconds=elapsed,**signature(y[fs+delay:2*fs+delay],fs,hz));results.append(r)
        d=[20*np.log10(x['fundamental_peak']/z['fundamental_peak']) for x,z in zip(results,base)];passed=sum(x['nonharmonic_db']<=max(-90,z['nonharmonic_db']+3) and abs(v)<=.1 for x,z,v in zip(results,base,d));r=dict(taps=n,edge=e,delay=delay,**m,passed=int(passed),worst_nonharmonic_db=max(x['nonharmonic_db'] for x in results),max_fundamental_difference_db=float(max(abs(np.array(d)))),median_time_ratio=float(np.median([x['seconds']/z['seconds'] for x,z in zip(results,base)])));summary.append(r);rows.extend(results);print(r,flush=True)
    Path('intermediate_filter_results.json').write_text(json.dumps(dict(renders=len(rows),summary=summary,results=rows),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
