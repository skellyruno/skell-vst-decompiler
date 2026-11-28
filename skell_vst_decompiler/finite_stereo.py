"""Finite complementary stereo excitation, independent waveform validation.
Original offline measurement; no plugin loading, implementation export or alignment fitting.
"""
import numpy as np
from scipy.fft import rfft, irfft, next_fast_len


def codes(n=4096, peak=.04):
    """Two orthogonal complementary code pairs, exact +/- peak at each sample."""
    if type(n) is not int or not 256<=n<=65536 or n & (n-1) or not 0<peak<=.25:
        raise ValueError('invalid code length or peak')
    a=b=np.ones(1)
    while len(a)<n:
        a,b=np.r_[a,b],np.r_[a,-b]
    return peak*np.stack((np.column_stack((a,b)),np.column_stack((-b[::-1],a[::-1]))))


def measure(x,y,repeat,hold_x,hold_y,fs,tail,*,tolerance=.01):
    """Two zero-padded code captures + repeat first + >=1 independent holdout.
    tail is declared support in samples, with additional >=100ms silence guard.
    Recovered finite response used only internally for prediction/route diagnostics.
    """
    x,y,repeat,hx,hy=map(lambda a:np.asarray(a,dtype=np.float64),(x,y,repeat,hold_x,hold_y))
    if type(fs) is not int or fs not in (44100,48000,96000) or type(tail) is not int or not 1<=tail<=12*fs or not 0<tolerance<=.1:
        raise ValueError('invalid support or rate')
    if x.ndim!=3 or x.shape[0]!=2 or x.shape[2]!=2 or y.shape!=x.shape or repeat.shape!=x[0].shape or hx.ndim!=3 or hx.shape!=hy.shape or not 1<=len(hx)<=4 or hx.shape[1:]!=x.shape[1:]:raise ValueError('invalid captures')
    m=x.shape[1]
    if m>14*fs or any(not np.isfinite(a).all() for a in (x,y,repeat,hx,hy)) or max(np.max(abs(y)),np.max(abs(repeat)),np.max(abs(hy)))>64 or np.max(abs(hx))>.5:raise ValueError('invalid samples')
    n=int(np.count_nonzero(x[0,:,0]));peak=float(np.max(abs(x)))
    expected=codes(n,peak)
    if m<n+tail+fs//10 or not np.array_equal(x[:,:n],expected) or np.any(x[:,n:]):raise ValueError('invalid finite code or guard')
    # Holdout must end early enough to leave the same full support and guard.
    if np.any(hx[:,m-tail-fs//10:]) or np.max(abs(hx))<1e-5 or any(np.array_equal(a,b) for a in hx for b in x):raise ValueError('invalid independent holdout')
    size=next_fast_len(m+n-1,real=True)
    X=rfft(x[:,:n],size,axis=1);Y=rfft(y,size,axis=1)
    # Complementarity and reversed second code give X*X = constant I.
    den=2*n*peak*peak
    H=np.einsum('cfi,cfo->foi',X.conj(),Y)/den
    h=irfft(H,size,axis=0)[:tail+1].copy()
    del X,Y,H
    HH=rfft(h,size,axis=0)
    def predict(a):
        # Only one capture transform at a time. The declared zero tail makes
        # the zero-padded linear convolution fit inside the FFT length.
        active=np.flatnonzero(np.any(a!=0,axis=1))
        stop=int(active[-1])+1 if len(active) else 1
        return irfft(np.einsum('fi,foi->fo',rfft(a[:stop],size,axis=0),HH),size,axis=0)[:m]
    def norm(a):return float(np.linalg.norm(a.ravel()))
    def relative(a,b):return norm(a-b)/max(norm(b),1e-15)
    rep=relative(repeat,y[0])
    def score(a,b):
        errors=[];total_error=total_ref=0.
        for u,v in zip(a,b):
            error=norm(predict(u)-v);ref=norm(v)
            errors.append(error/max(ref,1e-15));total_error+=error*error;total_ref+=ref*ref
        return float(np.sqrt(total_error)/max(np.sqrt(total_ref),1e-15)),errors
    train,_=score(x,y);held,individual=score(hx,hy)
    del HH
    # Output after excitation + declared support, including training, repeat and holdout.
    guard=0.
    from itertools import chain
    for a,b in chain(zip(x,y),((x[0],repeat),),zip(hx,hy)):
        active=np.flatnonzero(np.any(a!=0,axis=1));end=int(active[-1])+tail+1 if len(active) else 0
        guard=max(guard,norm(b[end:])/max(norm(b),1e-15))
    routes=[]
    for o in range(2):
        for i in range(2):
            v=h[:,o,i];p=float(np.max(abs(v)));routes.append(dict(input=i,output=o,peak=p,peak_sample=int(np.argmax(abs(v))) if p>1e-7 else None,energy=float(v@v)))
    status='CONSISTENT_FINITE_OBSERVATION'
    if max(norm(y),norm(hy))<1e-8:status='UNRESOLVED_SILENCE'
    elif rep>tolerance:status='UNSTABLE_REPEAT'
    elif guard>tolerance:status='TAIL_NOT_CONTAINED'
    elif max(train,held,*individual)>tolerance:status='HOLDOUT_OR_FIT_FAILED'
    return dict(status=status,code_samples=n,support_samples=tail,captures=3+len(hx),repeat_relative=rep,train_relative=train,holdout_relative=held,holdout_individual=individual,guard_relative=guard,routes=routes,note='Finite-support descriptive test; no unique topology inference or automatic alignment. Low-energy tails below gate may remain.')


def probes(fs=48000,tail_seconds=6,n=4096,peak=.04):
    if fs not in (44100,48000,96000) or type(tail_seconds) is not int or not 1<=tail_seconds<=12:raise ValueError('invalid rate or tail')
    a=codes(n,peak);tail=fs*tail_seconds;length=n+tail+fs//10
    x=np.pad(a,((0,0),(0,length-n),(0,0)))
    rng=np.random.default_rng(791);z=np.zeros((1,length,2));z[0,:n]=rng.uniform(-2*peak,2*peak,(n,2))
    return x,z,tail


def generate(folder,fs=48000,tail_seconds=6,n=4096,peak=.04):
    import hashlib,json
    from pathlib import Path
    import soundfile as sf
    x,z,tail=probes(fs,tail_seconds,n,peak);root=Path(folder);root.mkdir(parents=True,exist_ok=False)
    rows=[]
    for key,a in zip(('code_a','code_b','repeat_a','holdout'),(x[0],x[1],x[0],z[0])):
        path=root/(key+'.wav');sf.write(path,a,fs,subtype='FLOAT');rows.append(dict(id=key,file=path.name,family='finite_stereo',frames=len(a),channels=2,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),windows=[]))
    m=dict(schema=1,sample_rate=fs,support_samples=tail,code_samples=n,cases=rows,note='Separate fresh reset per file, exact length; no normalization. Preserve guard. Report active alignment and plugin settings.')
    (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m


def compare_host(folder,captures):
    """Read existing host_capture outputs; do not launch plugins. Metadata is not authenticated."""
    import re
    from pathlib import Path
    from .capture_intake import audio,read_json
    root=Path(folder);m=read_json(root/'manifest.json');keys=('code_a','code_b','repeat_a','holdout')
    fs=m['sample_rate'];tail=m['support_samples'];n=m['code_samples']
    if m['schema']!=1 or fs not in (44100,48000,96000) or type(tail) is not int or not 1<=tail<=12*fs or type(n) is not int or set(captures)!=set(keys) or len({Path(p).resolve() for p in captures.values()})!=4 or len(m['cases'])!=4:raise ValueError('invalid capture manifest')
    rows={r['id']:r for r in m['cases']};length=n+tail+fs//10
    if set(rows)!=set(keys):raise ValueError('invalid case list')
    fields=('binary_sha256','host_module_sha256','plugin','version','settings','parameter_readback','target_stage','host','block_size','alignment_status','reported_latency_samples','backend','reset')
    ident=None;xs=[];ys=[]
    for k in keys:
        r=rows[k];p=Path(captures[k]);v=read_json(p/'metadata.json');d=tuple(v[key] for key in fields)
        if ident is None:ident=d
        elif d!=ident:raise ValueError('capture identity changed')
        if v['backend']!='installed_vst3' or v['reset'] is not True or v['reported_latency_samples']!=0 or v['offset_samples']!=0 or v['sample_rate']!=fs or v['frames']!=length or r['frames']!=length or r['file']!=k+'.wav' or v['source_sha256']!=r['sha256'] or any(not isinstance(v[key],str) or not re.fullmatch('[0-9a-f]{64}',v[key]) for key in fields[:2]):raise ValueError('capture metadata or latency mismatch')
        a,_=audio(root/r['file'],fs,length,r['sha256']);b,_=audio(p/'render.wav',fs,length,v['render_sha256'])
        if read_json(p/'metadata.json')!=v:raise ValueError('capture metadata changed')
        xs.append(a);ys.append(b)
    if not np.array_equal(xs[0],xs[2]):raise ValueError('repeat source mismatch')
    if any(np.max(abs(y))>1.000001 for y in ys):return dict(status='REVIEW_REQUIRED',reason='output above full scale')
    result=measure(np.stack(xs[:2]),np.stack(ys[:2]),ys[2],np.stack(xs[3:]),np.stack(ys[3:]),fs,tail)
    result.update(evidence='host-declared observation only; active alignment and license not authenticated',alignment_status=ident[9],binary_sha256=ident[0],host_module_sha256=ident[1])
    return result


if __name__=='__main__':
    import argparse
    import json
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder');p.add_argument('--rate',type=int,default=48000);p.add_argument('--tail',type=int,default=6);p.add_argument('--code',type=int,default=4096);p.add_argument('--peak',type=float,default=.04);p.add_argument('--capture-map',type=Path);a=p.parse_args()
    if a.capture_map:print(json.dumps(compare_host(a.folder,json.loads(a.capture_map.read_text())),indent=2,allow_nan=False))
    else:generate(a.folder,a.rate,a.tail,a.code,a.peak)
