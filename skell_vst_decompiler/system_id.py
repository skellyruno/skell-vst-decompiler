"""Independent offline system identification, using explicitly aligned WAV pairs."""
import argparse
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.linalg import solve_toeplitz
from scipy.optimize import least_squares
from scipy.signal import chirp, lfilter, resample_poly
from .reference_lab import digest, measure, RATES


def history(fs, heldout=False):
    """Separate level/duration sequences, 10 ms coherent RMS windows."""
    if fs not in RATES: raise ValueError('Unsupported rate')
    if heldout not in (False,True,"test"): raise ValueError("Unknown history split")
    steps = [(100,-40),(3,-8),(65,-26),(90,-13),(180,-37),(60,-5),(120,-32)] if heldout=="test" else [(80,-36),(7,-6),(65,-36),(120,-12),(100,-42),(20,-4.5),(160,-27)] if not heldout else [(65,-39),(40,-15),(90,-33),(4,-4),(32,-21),(140,-9),(180,-39)]
    levels=np.repeat([l for n,l in steps],[n for n,l in steps]);n=round(fs*.01)
    tone=np.sin(2*np.pi*1000*np.arange(n*len(levels))/fs)
    x=tone*np.repeat(np.sqrt(2)*10**(levels/20),n)
    return np.column_stack((x,x))


def generate(root,fs=48000):
    root=Path(root);root.mkdir(parents=True,exist_ok=False);cases=[]
    for key,a in [('dynamic_train',history(fs)),('dynamic_holdout',history(fs,True)),('dynamic_test',history(fs,'test'))]:
        file=root/(key+'.wav');sf.write(file,a,fs,subtype='FLOAT')
        cases.append(dict(id=key,family='dynamics',file=file.name,sha256=digest(file),frames=len(a),channels=2,windows=[]))
    t=np.arange(4*fs)/fs
    x=.1*chirp(t,30,4,min(18000,.45*fs),method='logarithmic')*np.clip(np.minimum(t,4-t)*50,0,1)
    x=np.r_[x,np.zeros(fs)];z=np.zeros_like(x)
    for key,a in [('sweep_left_tail',np.column_stack((x,z))),('sweep_right_tail',np.column_stack((z,x)))]:
        file=root/(key+'.wav');sf.write(file,a,fs,subtype='FLOAT')
        cases.append(dict(id=key,family='linear',file=file.name,sha256=digest(file),frames=len(a),channels=2,windows=[]))
    m=dict(schema=1,sample_rate=fs,cases=cases,note='Original probes; reset between cases, retain tail, no normalization.')
    (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m


def envelope(a,b,fs):
    a,b=np.asarray(a,float),np.asarray(b,float);n=round(fs*.01)
    if fs not in RATES or a.shape!=b.shape or a.ndim!=2 or a.shape[1]!=2 or not 20*n<=len(a)<=120*fs or len(a)%n or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):raise ValueError('Invalid continuous histories')
    x=np.sqrt(np.mean(a.reshape(-1,n,2)**2,axis=(1,2)));y=np.sqrt(np.mean(b.reshape(-1,n,2)**2,axis=(1,2)))
    if np.min(x)<1e-6 or np.min(y)<1e-8:raise ValueError('Unobservable gain in silent block')
    return 20*np.log10(x),20*np.log10(y/x)


def predict(levels,p,dual=False):
    threshold,slope,makeup,attack,release=p[:5]
    target=makeup-slope*np.maximum(0,levels-threshold)
    def smooth(tau):
        s=makeup;out=[];a=-np.expm1(-10/attack);r=-np.expm1(-10/tau)
        for v in target:
            s+=(a if v<s else r)*(v-s);out.append(s)
        return np.asarray(out)
    fast=smooth(release)
    if not dual:return fast
    slow=smooth(release*p[5]);return (1-p[6])*fast+p[6]*slow


def fit_history(train,holdout):
    """Fit causal 10ms gain trajectories; validation history is never optimized."""
    x,y,xh,yh=(np.asarray(z,float) for z in (*train,*holdout))
    if any(z.ndim!=1 or not 20<=len(z)<=12000 or not np.all(np.isfinite(z)) for z in (x,y,xh,yh)) or x.shape!=y.shape or xh.shape!=yh.shape or np.ptp(x)<12 or np.ptp(xh)<12:raise ValueError('Insufficient history')
    results={}
    for dual in (False,True):
        lo=[-60,0,-24,1,10];hi=[0,.98,24,200,1500]
        seeds=[[-24,.7,0,10,100],[-30,.5,0,30,350]]
        if dual:lo += [1,0];hi += [10,1];seeds=[s+[4,.5] for s in seeds]
        fits=[least_squares(lambda p:predict(x,p,dual)-y,s,bounds=(lo,hi),max_nfev=160) for s in seeds]
        good=[f for f in fits if f.success]
        if not good:raise RuntimeError('No converged history fit')
        f=min(good,key=lambda f:f.cost);p=f.x
        rm=lambda v:float(np.sqrt(np.mean(v*v)))
        results['dual' if dual else 'single']={'threshold_db_rms':float(p[0]),'ratio':float(1/(1-p[1])),'makeup_db':float(p[2]),'attack_ms':float(p[3]),'release_ms':float(p[4]),'slow_release_ms':float(p[4]*p[5]) if dual else None,'slow_weight':float(p[6]) if dual else None,'train_rmse_db':rm(predict(x,p,dual)-y),'holdout_rmse_db':rm(predict(xh,p,dual)-yh),'parameters':p.tolist()}
    a,b=results['single'],results['dual']
    results['dual_preferred']=bool(a['holdout_rmse_db']-b['holdout_rmse_db']>max(.1,.2*a['holdout_rmse_db']) and b['slow_release_ms']>=2*b['release_ms'] and .05<b['slow_weight']<.95)
    results['note']='Descriptive gain smoothing at 10 ms; RMS includes distortion, times are model parameters, not internal states.'
    return results


def transfer(x,y,fs):
    """Regularized LTI spectral division, retaining phase and support flags."""
    x,y=np.asarray(x,float),np.asarray(y,float)
    if fs not in RATES or x.ndim!=1 or x.shape!=y.shape or not fs<=len(x)<=20*fs or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or np.max(np.abs(x))==0:raise ValueError('Invalid sweep pair')
    X=np.fft.rfft(x);Y=np.fft.rfft(y);power=np.abs(X)**2;floor=power.max()*1e-10
    H=Y*np.conj(X)/(power+floor);freq=np.fft.rfftfreq(len(x),1/fs);rows=[]
    for f in (63,125,250,500,1000,2000,4000,8000,12000,16000):
        k=int(np.argmin(abs(freq-f)));supported=bool(power[k]>100*floor)
        rows.append(dict(hz=float(freq[k]),supported=supported,magnitude_db=float(20*np.log10(max(abs(H[k]),1e-15))) if supported else None,phase_deg=float(np.angle(H[k],deg=True)) if supported and abs(H[k])>1e-12 else None))
    return rows


def formant_candidates(x,fs):
    """LPC envelope poles for stationary vowel-like audio, not phoneme labels."""
    x=np.asarray(x,float)
    if fs not in RATES or x.ndim!=1 or not round(.08*fs)<=len(x)<=10*fs or not np.all(np.isfinite(x)):raise ValueError('Invalid vowel window')
    from math import gcd
    g=gcd(fs,12000);z=resample_poly(x,12000//g,fs//g);z=z[len(z)//2-480:len(z)//2+480];z=lfilter([1,-.95],[1],z);z=(z-z.mean())*np.hanning(len(z))
    ac=np.array([np.dot(z[k:],z[:len(z)-k]) for k in range(15)])
    if ac[0]<1e-12:return []
    ac[0]*=1.000001;coef=solve_toeplitz(ac[:-1],-ac[1:]);poles=np.roots(np.r_[1.,coef]);rows=[]
    for p in poles:
        if p.imag<=0 or not 0<abs(p)<1:continue
        f=float(np.angle(p)*12000/(2*np.pi));bw=float(-np.log(abs(p))*12000/np.pi)
        if 200<=f<=3500 and 20<=bw<=500:rows.append({'hz':f,'bandwidth_hz':bw})
    return sorted(rows,key=lambda r:r['hz'])


def analyze(root,case,wet,meta):
    report=measure(root,case,wet,meta);fs=report['sample_rate'];dry=Path(root)/(case+'.wav')
    a,_=sf.read(dry,always_2d=True);b,_=sf.read(wet,start=meta['offset_samples'],frames=len(a),always_2d=True)
    if digest(dry)!=report['source_sha256'] or digest(wet)!=report['render_sha256']:raise ValueError('Changed pair')
    if case.startswith('dynamic_'):
        x,y=envelope(a,b,fs);report['history']={'levels_db':x.tolist(),'gain_db':y.tolist()}
    elif case.startswith('sweep_') and case.endswith('_tail'):
        ch=0 if case=='sweep_left_tail' else 1;report['lti_transfer']=[transfer(a[:,ch],b[:,i],fs) for i in range(2)]
        report['transfer_note']='Only valid for linear time-invariant response contained in recorded tail.'
    elif case=='vowel_like':
        report['formant_candidates']={'dry':formant_candidates(a[:,0],fs),'wet':formant_candidates(b[:,0],fs)}
    return report


def fit_reports(a,b,c=None):
    if a['case_id']!='dynamic_train' or b['case_id']!='dynamic_holdout' or a['sample_rate']!=b['sample_rate'] or a['source_sha256']==b['source_sha256'] or any(a['metadata'][k]!=b['metadata'][k] for k in ('plugin','version','settings','offset_samples')):raise ValueError('Different settings or invalid holdout')
    def h(r):return r['history']['levels_db'],r['history']['gain_db']
    result=fit_history(h(a),h(b))
    if c is not None:
        if c['case_id']!='dynamic_test' or c['sample_rate']!=a['sample_rate'] or c['source_sha256'] in (a['source_sha256'],b['source_sha256']) or any(a['metadata'][k]!=c['metadata'][k] for k in ('plugin','version','settings','offset_samples')):raise ValueError('Invalid independent test')
        x,y=map(lambda v:np.asarray(v,float),h(c))
        if x.ndim!=1 or x.shape!=y.shape or not 20<=len(x)<=12000 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):raise ValueError('Invalid test history')
        for name in ('single','dual'):
            result[name]['test_rmse_db']=float(np.sqrt(np.mean((predict(x,result[name]['parameters'],name=='dual')-y)**2)))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    g=s.add_parser('generate');g.add_argument('folder');g.add_argument('--rate',type=int,default=48000)
    m=s.add_parser('analyze');m.add_argument('folder');m.add_argument('case');m.add_argument('wet');m.add_argument('metadata')
    f=s.add_parser('fit');f.add_argument('train');f.add_argument('holdout');f.add_argument('--test');args=p.parse_args()
    load=lambda x:json.loads(Path(x).read_text())
    if args.cmd=='generate':r=generate(args.folder,args.rate)
    elif args.cmd=='analyze':r=analyze(args.folder,args.case,args.wet,load(args.metadata))
    else:r=fit_reports(load(args.train),load(args.holdout),load(args.test) if args.test else None)
    print(json.dumps(r,indent=2,allow_nan=False))


if __name__=='__main__':main()
