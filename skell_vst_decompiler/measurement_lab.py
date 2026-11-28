"""Independent bounded measurement experiments for owned and authorized audio."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scipy.signal import fftconvolve, coherence, welch
from scipy.interpolate import RBFInterpolator


def sweep(fs=48000, seconds=3, peak=.3):
    """Known exponential phase; three harmonics below Nyquist at supported rates."""
    if fs not in (44100,48000,96000) or type(seconds) is not int or not 2<=seconds<=10 or not 0<peak<=.5:
        raise ValueError('invalid sweep settings')
    n=fs*seconds; L=seconds/np.log(50.); t=np.arange(n)/fs
    x=peak*np.sin(2*np.pi*100*L*np.expm1(t/L))
    fade=round(.01*fs); ramp=np.sin(np.linspace(0,np.pi/2,fade))**2
    x[:fade]*=ramp;x[-fade:]*=ramp[::-1]
    inv=x[::-1]*np.exp(-t/L)
    inv/=fftconvolve(x,inv)[n-1]
    return x,inv,L


def harmonic_windows(x,y,inv,L,fs,latency=0):
    """Energy near known harmonic arrival times, not calibrated THD or full IR."""
    x,y,inv=map(lambda v:np.asarray(v,float),(x,y,inv))
    if x.ndim!=1 or y.ndim!=1 or inv.shape!=x.shape or not 1<=len(x)<=960000 or not len(x)<=len(y)<=len(x)+10*fs or not np.isfinite(np.r_[x,y,inv]).all() or not 0<L<=10 or fs not in (44100,48000,96000) or type(latency) is not int or not 0<=latency<=fs:
        raise ValueError('invalid sweep capture')
    z=fftconvolve(y,inv);center=len(x)-1+latency;half=round(.005*fs)
    rows=[]
    for order in (1,2,3):
        c=center-round(fs*L*np.log(order)); a,b=c-half,c+half+1
        if a<0 or b>len(z):raise ValueError('harmonic window outside capture')
        w=z[a:b];rows.append(dict(order=order,center_sample=c,window_energy=float(w@w),peak=float(max(abs(w)))))
    denom=max(rows[0]['window_energy'],1e-30)
    for r in rows:r['relative_window_db']=float(10*np.log10(max(r['window_energy']/denom,1e-30)))
    return rows


def coherence_gate(x,y,fs,minimum=.95):
    """Welch magnitude-squared coherence on excited bins; diagnostic only."""
    x,y=map(lambda v:np.asarray(v,float),(x,y))
    if x.ndim!=1 or x.shape!=y.shape or not 16384<=len(x)<=2000000 or not np.isfinite(np.r_[x,y]).all() or fs not in (44100,48000,96000) or not 0<minimum<1:
        raise ValueError('invalid coherence capture')
    f,p=welch(x,fs,nperseg=2048);_,c=coherence(x,y,fs,nperseg=2048)
    active=(f>=100)&(f<=min(16000,fs*.4))&(p>max(p)*1e-4)&np.isfinite(c)
    if not active.any():raise ValueError('no excited bins')
    v=c[active];return dict(bins=int(len(v)),median=float(np.median(v)),p10=float(np.quantile(v,.1)),pass_fraction=float(np.mean(v>=minimum)))


def model_screen(train_x,train_y,test_x,test_y):
    """Fixed input-only polynomial lag bases; fit train, predict unseen sequences."""
    def design(x,y):
        x,y=map(lambda v:np.asarray(v,float),(x,y))
        if x.ndim!=1 or x.shape!=y.shape or not 32<=len(x)<=500000 or not np.isfinite(np.r_[x,y]).all() or max(abs(x))>2:
            raise ValueError('invalid model sequence')
        a=np.column_stack([x[4-i:len(x)-i] for i in range(5)])
        return a,y[4:]
    a,b=design(train_x,train_y);c,d=design(test_x,test_y)
    if np.array_equal(train_x,test_x):raise ValueError('distinct heldout input required')
    def basis(x,k):
        p=x[:,:1];cols=[x]
        if k>=1:cols.extend((p*p,p**3,p**5))
        if k>=2:cols.extend((x[:,1:]**2,x[:,1:]**3,p*x[:,1:]))
        return np.column_stack(cols)
    out=[]
    for k,name in enumerate(('linear_fir','static_color_plus_fir','nonlinear_memory')):
        A,B=basis(a,k),basis(c,k);w,_,rank,_=np.linalg.lstsq(A,b,rcond=1e-10)
        if rank!=A.shape[1]:raise ValueError('rank deficient model')
        out.append(dict(model=name,terms=A.shape[1],train_rms=float(np.sqrt(np.mean((A@w-b)**2))),holdout_rms=float(np.sqrt(np.mean((B@w-d)**2)))))
    return out


def sample_surface(grid, observe, hold_x, *, budget=25, adaptive=True):
    """Select only measured candidates. Holdout labels never enter selection."""
    x,z=np.asarray(grid,float),np.asarray(hold_x,float)
    if x.ndim!=2 or x.shape[1]!=2 or z.ndim!=2 or z.shape[1]!=2 or not 9<=budget<=len(x)<=4096 or not 1<=len(z)<=4096 or not np.isfinite(np.r_[x,z]).all() or np.max(abs(np.r_[x,z]))>1 or len(set(map(tuple,x)))!=len(x) or set(map(tuple,x))&set(map(tuple,z)):
        raise ValueError('invalid candidate or holdout coordinates')
    chosen=[];values=[];targets=np.array([[-1,-1],[-1,1],[1,-1],[1,1],[0,0],[-1,0],[1,0],[0,-1],[0,1]])
    for q in targets:
        i=int(np.argmin(np.sum((x-q)**2,axis=1)))
        if i in chosen:raise ValueError('initial design degenerate')
        chosen.append(i);values.append(float(observe(x[i])))
    if not np.isfinite(values).all():raise ValueError('nonfinite observation')
    def poly(v):return np.column_stack((np.ones(len(v)),v,v[:,0]*v[:,1],v*v))
    while len(chosen)<budget:
        a=x[chosen];v=np.asarray(values);dist=np.min(np.linalg.norm(x[:,None,:]-a[None,:,:],axis=2),axis=1)
        score=dist.copy()
        if adaptive:
            r=RBFInterpolator(a,v,kernel='thin_plate_spline',smoothing=1e-9)
            w=np.linalg.lstsq(poly(a),v,rcond=None)[0]
            diff=abs(r(x)-poly(x)@w);score*=1+diff/max(np.median(diff),.01)
        score[chosen]=-1;i=int(np.argmax(score));chosen.append(i);values.append(float(observe(x[i])))
        if not np.isfinite(values[-1]):raise ValueError('nonfinite observation')
    return chosen,RBFInterpolator(x[chosen],values,kernel='thin_plate_spline',smoothing=1e-9)(z)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def cached(root,identity,compute):
    """Local JSON measurement cache, explicit input/code/settings/version fingerprint.
    Caller supplies complete identity; integrity is not authentication. No raw audio.
    """
    required={'source_sha256','implementation_sha256','settings','versions'}
    if not isinstance(identity,dict) or set(identity)!=required or any(not isinstance(identity[k],str) or len(identity[k])!=64 or any(c not in '0123456789abcdef' for c in identity[k]) for k in ('source_sha256','implementation_sha256')):
        raise ValueError('incomplete cache identity')
    key=hashlib.sha256(canonical(identity)).hexdigest();root=Path(root);root.mkdir(parents=True,exist_ok=True);path=root/(key+'.json')
    if path.exists():
        record=json.loads(path.read_text());payload=record['payload']
        if record['key']!=key or record['sha256']!=hashlib.sha256(canonical(payload)).hexdigest():raise ValueError('cache integrity mismatch')
        return payload,True
    payload=compute();record={'key':key,'payload':payload,'sha256':hashlib.sha256(canonical(payload)).hexdigest()}
    with tempfile.NamedTemporaryFile(dir=root,delete=False) as f:
        temp=Path(f.name);f.write(canonical(record));f.flush();os.fsync(f.fileno())
    try:os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)
    return payload,False


def parallel_measure(jobs, worker, workers=2):
    """Bounded independent offline jobs only. Do not share plugin instances."""
    if not 1<=len(jobs)<=256 or type(workers) is not int or not 1<=workers<=4:raise ValueError('invalid batch size')
    with ThreadPoolExecutor(max_workers=workers) as pool:return list(pool.map(worker,jobs))
