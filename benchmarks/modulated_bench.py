import argparse,json,math
from pathlib import Path
import numpy as np,pedalboard as pb,soundfile as sf
from scipy.signal import resample_poly
from scipy.interpolate import lagrange
from experiments.modulated_identification import predict,select
from experiments.multirate_diagnostic import color,signature

def oracle(x,fs,p,kind):
    # Independent polynomial coefficient evaluation using integer sample indices.
    t=np.arange(len(x));pos=t-(p[0]+p[1]*np.sin(2*np.pi*p[2]*t/fs+p[3]))*fs/1000
    i=np.floor(pos).astype(int);u=pos-i;nodes=np.array([0,1] if kind=='linear' else [-1,0,1,2]);out=np.zeros(len(x))
    for j in nodes:
        a=np.zeros(len(nodes));a[nodes==j]=1;weights=lagrange(nodes,a)(u);ind=i+j;valid=(ind>=0)&(ind<len(x));out[valid]+=weights[valid]*x[ind[valid]]
    return p[4]*out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('sources',nargs=3,type=Path);args=ap.parse_args()
    rng=np.random.default_rng(139);p=[7.4,.8,.91,.4,.73];rows=[];counts={'oracle':0,'pedalboard':0,'multirate':0};files=args.sources
    a=rng.uniform(-.7,.7,48000*2);b=rng.uniform(-.6,.6,44100*2)
    def real(x,fs,kind):
        counts['oracle']+=1;return oracle(x,fs,p,kind)
    def chorus(x,fs):
        counts['pedalboard']+=1;return pb.Chorus(rate_hz=.91,depth=.3,centre_delay_ms=7.4,feedback=0,mix=1).process(x.astype(np.float32)[None,:],fs,buffer_size=128,reset=True)[0].astype(float)
    for kind in ('linear','cubic','chorus'):
        f=chorus if kind=='chorus' else lambda x,fs:real(x,fs,kind)
        y,w=f(a,48000),f(b,44100)
        try:r=select((a,y,48000),(b,w,44100))
        except ValueError as e:r={'selected':None,'reason':str(e)}
        print(kind,r,flush=True);hold=[]
        if r['selected']:
            for fs in (44100,48000,96000,192000):
                for i,name in enumerate(files):
                    x,sr=sf.read(name,always_2d=True);g=math.gcd(sr,fs);x=resample_poly(x[:sr,0],fs//g,sr//g);y=f(x,fs);hold.append(dict(rate=fs,source=i,relative_rms={c['kind']:float(np.linalg.norm(predict(x,fs,c['parameters'],c['kind'])-y)/np.linalg.norm(y)) for c in r['candidates']}))
        rows.append(dict(fixture=kind,fit=r,holdout=hold))
    alias=[]
    for fs in (44100,48000,96000):
        for hz in (int(fs*.17)+1,int(fs*.211)+1,int(fs*.31)+1):
            for level in (.2,.7):
                x=level*np.sin(2*np.pi*hz*np.arange(fs*3)/fs)
                for factor in (1,2,4,8,16):
                    y=color(x,factor);counts['multirate']+=1;alias.append(dict(rate=fs,hz=hz,level=level,factor=factor,**signature(y[fs:2*fs],fs,hz)))
                y=pb.Distortion(drive_db=20*np.log10(4)).process(x.astype(np.float32)[None,:],fs,buffer_size=128,reset=True)[0];counts['pedalboard']+=1;alias.append(dict(rate=fs,hz=hz,level=level,factor='fixture',**signature(y[fs:2*fs],fs,hz)))
    Path('results.json').write_text(json.dumps(dict(scope='original interpolation oracle and independent Pedalboard fixtures, no commercial captures',counts=counts,modulation=rows,alias=alias),indent=2,allow_nan=False)+'\n');print(counts,flush=True)
if __name__=='__main__':main()
