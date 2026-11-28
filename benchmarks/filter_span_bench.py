"""Compare antialias filter length at fixed factor, coherent finite tone measurements."""
import json,time
from pathlib import Path
import numpy as np
from experiments.multirate_diagnostic import color,signature

def main():
    rows=[]
    for fs in (44100,48000,96000):
        for ratio in (.17,.211,.31,.45,.49):
            hz=int(fs*ratio)+1;t=np.arange(3*fs)/fs
            for level in (.02,.7):
                x=level*np.sin(2*np.pi*hz*t)
                for span in (10,40,100,200):
                    start=time.perf_counter();y=color(x,4,span=span);elapsed=time.perf_counter()-start
                    rows.append(dict(rate=fs,hz=hz,ratio=ratio,level=level,span=span,seconds=elapsed,**signature(y[fs:2*fs],fs,hz)))
    Path('filter_span_results.json').write_text(json.dumps(dict(scope='original offline 4x FIR tanh diagnostic; no production latency or commercial match',renders=len(rows),results=rows),indent=2,allow_nan=False)+'\n')
    for s in (10,40,100,200):
        r=[x for x in rows if x['span']==s and x['ratio']==.17 and x['level']==.7];print(s,[x['nonharmonic_db'] for x in r])
if __name__=='__main__':main()
