"""Equal input, 4x saturation, full coherent middle segment; independent diagnostics."""
import argparse,json,time
from pathlib import Path
import numpy as np
from experiments.staged_color import staged,response
from experiments.multirate_diagnostic import color,signature

def main():
    p=argparse.ArgumentParser();p.add_argument('--rate',type=int,choices=(44100,48000,96000),required=True);a=p.parse_args();fs=a.rate
    configs=[(321,.48),(481,.49),(641,.49)]
    responses=[response(n,e) for n,e in configs]+[response(65,.3)]
    rows=[]
    for ratio in (.17,.211,.31,.45,.49):
        hz=int(fs*ratio)+1;t=np.arange(fs*3)/fs
        for level in (.02,.7):
            x=level*np.sin(2*np.pi*hz*t)
            for name,fn in [('direct1601',lambda:color(x,4,span=200)),*[(f'staged{n}',lambda n=n,e=e:staged(x,n,e)) for n,e in configs]]:
                start=time.perf_counter();y=fn();elapsed=time.perf_counter()-start;rows.append(dict(rate=fs,ratio=ratio,hz=hz,level=level,model=name,seconds=elapsed,**signature(y[fs:2*fs],fs,hz)))
    Path(f'staged_{fs}.json').write_text(json.dumps(dict(scope='original offline 4x tone tests, no commercial match',renders=len(rows),responses=responses,results=rows),indent=2,allow_nan=False)+'\n')
    for name in ('direct1601','staged321','staged481','staged641'):
        r=[x for x in rows if x['model']==name];print(fs,name,'median time',np.median([x['seconds'] for x in r]),'worst spectral',max(x['nonharmonic_db'] for x in r),'selected',[(x['nonharmonic_db'],x['fundamental_peak']) for x in r if x['ratio']==.17 and x['level']==.7],flush=True)
if __name__=='__main__':main()
