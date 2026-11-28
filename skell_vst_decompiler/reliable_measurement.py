"""Independent offline diagnostics; no plugin loading or internal DSP inference."""
import hashlib
import threading
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.signal import csd, welch


def harmonic_levels(x, y, fs, hz, orders=5):
    """Coherent single-tone amplitude/phase, RMS residual and THD within selected orders.
    Supply a settled integer-period segment; no fitted delay or normalization.
    """
    x,y=np.asarray(x,float),np.asarray(y,float)
    if type(fs)!=int or type(hz)!=int or type(orders)!=int or not 8000<=fs<=192000 or not 20<=hz or not 2<=orders<=10 or orders*hz>=fs/2 or x.ndim!=1 or x.shape!=y.shape or not fs//10<=len(x)<=4*fs or len(x)*hz%fs or not np.isfinite(np.r_[x,y]).all():
        raise ValueError('invalid coherent segment')
    n=len(x); bins=np.arange(1,orders+1)*(n*hz//fs)
    X,Y=np.fft.rfft(x)/n,np.fft.rfft(y)/n
    if abs(X[bins[0]])<1e-8:raise ValueError('missing excitation')
    if np.linalg.norm(np.delete(X,[bins[0]]))>1e-5*abs(X[bins[0]]):raise ValueError('input not a pure coherent tone')
    a=2*abs(Y[bins]);fund=a[0]
    if fund<1e-10:raise ValueError('unresolved fundamental')
    residual=Y.copy();residual[0]=0;residual[bins]=0
    # One-sided Parseval; Nyquist has no conjugate partner for even lengths.
    weights=np.full(len(Y),2.);weights[0]=1
    if n%2==0:weights[-1]=1
    return dict(fundamental_gain_db=float(20*np.log10(abs(Y[bins[0]]/X[bins[0]]))),phase_rad=float(np.angle(Y[bins[0]]/X[bins[0]])),harmonic_peak=a.tolist(),thd_selected=float(np.linalg.norm(a[1:])/fund),other_ac_rms=float(np.sqrt(np.sum(weights*abs(residual)**2))))


def repeated_spectrum(x, outputs, fs):
    """Separate repeat disagreement from coherence on fixed aligned observations."""
    x=np.asarray(x,float);y=np.asarray(outputs,float)
    if x.ndim!=1 or y.ndim!=2 or y.shape[1]!=len(x) or not 2<=len(y)<=8 or not 16384<=len(x)<=1000000 or not np.isfinite(x).all() or not np.isfinite(y).all() or fs not in (44100,48000,96000):raise ValueError('invalid repeated spectrum')
    f,px=welch(x,fs,nperseg=2048);active=(f>=100)&(f<=min(16000,fs*.4))&(px>max(px)*1e-4)
    if not active.any():raise ValueError('no excitation')
    h=[];co=[]
    for v in y:
        _,py=welch(v,fs,nperseg=2048);_,p=csd(x,v,fs,nperseg=2048)
        h.append(p[active]/px[active]);co.append(np.divide(abs(p[active])**2,px[active]*py[active],out=np.zeros(int(active.sum())),where=py[active]>1e-24))
    h=np.asarray(h);co=np.clip(co,0,1);mean=h.mean(axis=0)
    if np.linalg.norm(mean)<1e-10:raise ValueError('unresolved response')
    disagree=max(float(np.linalg.norm(v-mean)/np.linalg.norm(mean)) for v in h)
    return dict(bins=int(active.sum()),worst_coherence_pass_fraction=float(np.min(np.mean(co>=.95,axis=1))),response_repeat_relative=disagree,status='CONSISTENT' if disagree<=.01 and np.min(np.mean(co>=.95,axis=1))>=.95 else 'UNRELIABLE')


def static_descriptions(train_x,train_y,validation_x,validation_y,test_x,test_y):
    """Fit polynomial or local monotone cubic interpolation to training only.
    Choose using validation; score separate final test. No extrapolation or alignment.
    Only a descriptive memoryless approximation, not a production model.
    """
    pairs=[(np.asarray(x,float),np.asarray(y,float)) for x,y in ((train_x,train_y),(validation_x,validation_y),(test_x,test_y))]
    for x,y in pairs:
        if x.ndim!=1 or x.shape!=y.shape or not 32<=len(x)<=500000 or not np.isfinite(np.r_[x,y]).all():raise ValueError('invalid sequences')
    x,y=pairs[0];v,w=pairs[1];z,q=pairs[2]
    if len(x)<258:raise ValueError('insufficient training samples')
    if any(np.array_equal(a,b) for a,b in ((x,v),(v,z),(x,z))) or min(v.min(),z.min())<x.min() or max(v.max(),z.max())>x.max():raise ValueError('independent in-range test required')
    a,b=x.min(),x.max();scale=max(abs(a),abs(b));u=x/scale
    models=[]
    for degree in (1,5,9):
        c=np.polynomial.chebyshev.chebfit(u,y,degree);models.append((f'chebyshev_{degree}',lambda k,c=c:np.polynomial.chebyshev.chebval(k/scale,c)))
    # Group sorted inputs into equal-count bins; use median coordinate and output.
    order=np.argsort(x);groups=np.array_split(order,129);knots=np.array([np.median(x[g]) for g in groups]);values=np.array([np.median(y[g]) for g in groups])
    if np.any(np.diff(knots)<=0):raise ValueError('insufficient training diversity')
    interp=PchipInterpolator(np.r_[a,knots,b],np.r_[y[order[0]],values,y[order[-1]]],extrapolate=False)
    models.append(('pchip_129',interp))
    rms=lambda r:float(np.sqrt(np.mean(r*r)))
    scores=[dict(model=name,validation_rms=rms(fn(v)-w)) for name,fn in models];i=min(range(len(scores)),key=lambda k:scores[k]['validation_rms'])
    return dict(validation=scores,selected=scores[i]['model'],final_test_rms=rms(models[i][1](z)-q),linear_final_test_rms=rms(models[0][1](z)-q))


class SingleFlightCache:
    """Coalesce equal keys within one process. Existing durable cache stays unchanged."""
    def __init__(self,root):
        self.root=Path(root);self._locks={};self._guard=threading.Lock()

    def get(self,identity,compute):
        from .measurement_lab import cached,canonical
        key=hashlib.sha256(canonical(identity)).hexdigest()
        with self._guard:
            lock,count=self._locks.get(key,(threading.Lock(),0));self._locks[key]=(lock,count+1)
        try:
            with lock:return cached(self.root,identity,compute)
        finally:
            with self._guard:
                _,count=self._locks[key]
                if count==1:del self._locks[key]
                else:self._locks[key]=(lock,count-1)
