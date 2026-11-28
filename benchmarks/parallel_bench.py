"""Independent built-in and original scalar fixtures; private inputs never committed."""
import argparse,json,math
from pathlib import Path
import numpy as np,pedalboard as pb,soundfile as sf
from scipy.signal import resample_poly
from experiments.parallel_identification import select,predict,fit_echo,delayed

def main():
    ap=argparse.ArgumentParser();ap.add_argument('sources',nargs='+');ap.add_argument('--output',required=True);a=ap.parse_args()
    rng=np.random.default_rng(655);rows=[];renders=0
    def proc(f,x,fs):
        nonlocal renders
        renders+=1
        return f.process(np.ascontiguousarray(x[None,:],dtype=np.float32),fs,buffer_size=128,reset=True)[0].astype(float)
    def render(x,fs,k):
        if k=='control':return proc(pb.Compressor(threshold_db=-24,ratio=4,attack_ms=5,release_ms=120),x,fs)
        low=proc(pb.LowpassFilter(cutoff_frequency_hz=2800),x,fs)
        color=proc(pb.Distortion(drive_db=14),low,fs)*.37
        if k=='wet':return color
        if k=='parallel':return .56*x+color
        return color+.61*proc(pb.Distortion(drive_db=5),x-low,fs)
    def obs(k,settings):
        out=[]
        for fs,i in settings:
            t=np.arange(fs//10)/fs
            x=rng.uniform(-.8,.8,len(t)) if i==0 else .55*np.sin(2*np.pi*(353+100*i)*t)+.21*np.sin(2*np.pi*(5311+431*i)*t)+.06*rng.uniform(-1,1,len(t))
            out.append((x,render(x,fs,k),fs))
        return out
    def err(x,y):return float(np.linalg.norm(x-y)/max(np.linalg.norm(y),1e-12))
    sources=[]
    for fs in (44100,48000,96000,192000):
        for i,path in enumerate(a.sources):
            x,sr=sf.read(path,always_2d=True);g=math.gcd(fs,sr);x=resample_poly(x[:sr,0],fs//g,sr//g);sources.append((fs,i,x))
    for k in ('wet','parallel','split','control'):
        r=select(obs(k,[(48000,0),(48000,1)]),obs(k,[(44100,2),(96000,3)]));hold=[]
        if r['selected']:
            for fs,i,x in sources:
                y=render(x,fs,k)
                hold.append(dict(rate=fs,source=i,errors={c['kind']:err(predict(x,fs,c['kind'],c['parameters']),y) for c in r['candidates'] if c['converged']}))
        rows.append(dict(fixture=k,fit=r,holdout=hold));print(k,r['selected'],flush=True)
    def oracle(x,d,g,s,k):
        y=np.zeros_like(x)
        for i in range(d,len(x)):
            v=y[i-d];y[i]=x[i-d]+g*(np.tanh(s*v)/s if k=='inside' else v)
        return np.tanh(s*y)/s if k=='outside' else y
    echo=[];count=0
    for k in ('linear','inside','outside'):
        d=137;g=.74;s=3.2;imp=np.zeros(4096);imp[0]=.7
        tr=rng.uniform(-.85,.85,4096);va=rng.uniform(-.7,.7,4096)
        r=fit_echo(oracle(imp,d,g,s,k),[(tr,oracle(tr,d,g,s,k))],[(va,oracle(va,d,g,s,k))]);count+=3;hold=[]
        for fs,i,x in sources:
            n=round(d*fs/48000);y=oracle(x,n,g,s,k);count+=1
            hold.append(dict(rate=fs,source=i,errors={c['kind']:err(delayed(x,n,c['parameters'][0],c['parameters'][1] if len(c['parameters'])>1 else 1.,c['kind']),y) for c in r['candidates'] if c['converged']}))
        echo.append(dict(fixture=k,fit=r,holdout=hold));print('echo',k,r['selected'],flush=True)
    Path(a.output).write_text(json.dumps(dict(scope='independent built-in and original scalar fixtures; no commercial match',pedalboard_renders=renders,original_echo_observations=count,parallel=rows,echo=echo),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
