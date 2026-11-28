"""Original periodic stereo measurement for owned/authorized observations.
No plugin loading, automatic alignment, or internal architecture inference.
"""
import numpy as np
from scipy.fft import rfft, irfft


def stimulus(n, seed, peak=.1):
    """Two sign-coded, three-period broadband inputs with nonzero bins."""
    if type(n) is not int or not 256 <= n <= 1048576 or n % 2 or not 0 < peak <= .5:
        raise ValueError('invalid probe size or level')
    rng = np.random.default_rng(seed)
    s = np.exp(1j*rng.uniform(-np.pi, np.pi, n//2+1)); s[[0,-1]] = 1
    a = irfft(s, n); a *= peak / np.max(abs(a))
    return np.stack([np.tile(np.column_stack((a, sign*a)), (3,1)) for sign in (1,-1)])


def _capture(x, y):
    x, y = np.asarray(x,float), np.asarray(y,float)
    if x.ndim != 3 or x.shape[0]!=2 or x.shape[2]!=2 or x.shape!=y.shape or x.shape[1]%3 or not np.isfinite(x).all() or not np.isfinite(y).all() or np.max(abs(x))>.500001 or np.max(abs(y))>64:
        raise ValueError('invalid aligned captures')
    n=x.shape[1]//3
    if not 256<=n<=1048576 or n%2:raise ValueError('invalid period')
    a=x[0,:n,0]; expected=np.stack([np.tile(np.column_stack((a, sign*a)),(3,1)) for sign in (1,-1)])
    if not np.array_equal(x,expected):raise ValueError('incorrect stereo sign code or repeated stimulus')
    A=rfft(a)
    if np.min(abs(A)) < np.max(abs(A))*1e-5 or np.max(abs(A))<1e-12:
        raise ValueError('missing excitation bins')
    return n,A,y


def measure(x,y,hold_x,hold_y,*,tolerance=.01):
    """Return aggregate response diagnostics only. Two train and two holdout captures.
    Holdout uses independent phase and/or level. Period must exceed relevant memory;
    stable periodic observations cannot distinguish a delay from its modulo-period alias.
    """
    if not np.isfinite(tolerance) or not 0<tolerance<=.1:raise ValueError('invalid tolerance')
    n,A,y=_capture(x,y); m,B,z=_capture(hold_x,hold_y)
    if n!=m or np.allclose(A/np.linalg.norm(A),B/np.linalg.norm(B),rtol=1e-8,atol=1e-10):raise ValueError('independent holdout phase required')
    rms=lambda a:float(np.sqrt(np.mean(a*a)))
    scale=max(rms(y[:,-n:]),rms(z[:,-n:]),1e-15)
    # Two repeated periods checked independently; average only after measuring repeat error.
    rep=max(rms(v[:,n:2*n]-v[:,2*n:])/max(rms(v[:,2*n:]),1e-15) for v in (y,z))
    def spectra(v):return rfft(.5*(v[:,n:2*n]+v[:,2*n:]),axis=1)
    Y,Z=spectra(y),spectra(z)
    h=np.stack(((Y[0]+Y[1])/(2*A[:,None]),(Y[0]-Y[1])/(2*A[:,None])),axis=2)
    k=np.stack(((Z[0]+Z[1])/(2*B[:,None]),(Z[0]-Z[1])/(2*B[:,None])),axis=2)
    pred=irfft(np.stack((B[:,None]*(h[:,:,0]+h[:,:,1]),B[:,None]*(h[:,:,0]-h[:,:,1]))),n,axis=1)
    ref=.5*(z[:,n:2*n]+z[:,2*n:])
    residual=rms(pred-ref)/max(rms(ref),1e-15)
    drift=float(np.linalg.norm(k-h)/max(np.linalg.norm(k),1e-15))
    # Per-route spectral energy and heldout discrepancy, no exported implementation.
    routes=[]
    for o in range(2):
        for i in range(2):
            v,w=h[:,o,i],k[:,o,i]; mag=float(np.sqrt(np.mean(abs(v)**2)))
            routes.append({'output':o,'input':i,'spectral_rms':mag,'absolute_spectral_disagreement':float(np.sqrt(np.mean(abs(v-w)**2)))})
    status='UNRESOLVED_SILENCE' if scale<1e-9 else 'UNSTABLE_PERIODS' if rep>tolerance else 'HOLDOUT_FAILED' if max(residual,drift)>tolerance else 'CONSISTENT_OBSERVATION'
    return {'status':status,'period_samples':n,'bins':n//2+1,'capture_count':4,'repeat_relative_rms':rep,'heldout_relative_rms':residual,'spectral_relative_disagreement':drift,'routes':routes,'note':'Periodic consistency only; not proof of time invariance or internal implementation. No alignment fitted. Tail longer than period can wrap.'}


def generate(folder,fs=48000,seconds=1):
    """Four original WAVs and manifest for the existing supported-host capture tool."""
    import hashlib,json
    from pathlib import Path
    import soundfile as sf
    if fs not in (44100,48000,96000) or type(seconds) is not int or not 1<=seconds<=10:raise ValueError('invalid capture rate or period')
    n=fs*seconds
    x,z=stimulus(n,1,.12),stimulus(n,2,.35)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False);rows=[]
    for label,v in [('train',x),('holdout',z)]:
        for i,sign in enumerate(('plus','minus')):
            key=label+'_'+sign;path=folder/(key+'.wav');sf.write(path,v[i],fs,subtype='FLOAT')
            rows.append(dict(id=key,family='broadband',file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),frames=3*n,channels=2,windows=[]))
    manifest=dict(schema=1,sample_rate=fs,cases=rows,note='Four original stereo sign-coded stimuli. Render each from fresh reset, preserve exact length, do not normalize. Period must exceed relevant system memory.')
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest


def compare_files(folder,captures,**kwargs):
    """Verify manifest and four existing host capture folders. Metadata not authentication."""
    import hashlib,json,re
    from pathlib import Path
    import soundfile as sf
    keys=('train_plus','train_minus','holdout_plus','holdout_minus')
    if set(captures)!=set(keys) or len({Path(p).resolve() for p in captures.values()})!=4:raise ValueError('four distinct capture folders required')
    folder=Path(folder);manifest=json.loads((folder/'manifest.json').read_text());fs=manifest['sample_rate']
    if manifest['schema']!=1 or fs not in (44100,48000,96000) or len(manifest['cases'])!=4:raise ValueError('invalid manifest')
    rows={r['id']:r for r in manifest['cases']}
    if set(rows)!=set(keys):raise ValueError('invalid cases')
    fields=('binary_sha256','host_module_sha256','plugin','version','settings','parameter_readback','target_stage','host','block_size','alignment_status','reported_latency_samples','backend','reset')
    identity=None;x=[];y=[]
    for key in keys:
        row=rows[key];path=folder/(key+'.wav');wet=Path(captures[key])/'render.wav';meta=Path(captures[key])/'metadata.json';raw=meta.read_bytes();m=json.loads(raw)
        ident=tuple(m[k] for k in fields)
        if identity is None:identity=ident
        elif identity!=ident:raise ValueError('capture identity or settings changed')
        if m['backend']!='installed_vst3' or m['reset'] is not True or m['reported_latency_samples']!=0 or m['offset_samples']!=0 or m['sample_rate']!=fs or any(not isinstance(m[k],str) or not re.fullmatch('[0-9a-f]{64}',m[k]) for k in fields[:2]):raise ValueError('unsupported capture identity or latency')
        def read(p,sha):
            if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise ValueError('audio hash mismatch')
            info=sf.info(p)
            if info.samplerate!=fs or info.channels!=2 or info.frames!=row['frames'] or not 768<=info.frames<=3145728:raise ValueError('audio format mismatch')
            a,_=sf.read(p,always_2d=True)
            if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise ValueError('audio changed during read')
            return a
        if row['file']!=path.name or m['source_sha256']!=row['sha256'] or m['frames']!=row['frames']:raise ValueError('source or render mismatch')
        x.append(read(path,row['sha256']));y.append(read(wet,m['render_sha256']))
        if meta.read_bytes()!=raw:raise ValueError('metadata changed during read')
    r=measure(np.stack(x[:2]),np.stack(y[:2]),np.stack(x[2:]),np.stack(y[2:]),**kwargs)
    r.update(sample_rate=fs,binary_sha256=identity[0],host_module_sha256=identity[1]);return r


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    g=s.add_parser('generate');g.add_argument('folder');g.add_argument('--rate',type=int,default=48000);g.add_argument('--seconds',type=int,default=1)
    m=s.add_parser('measure');m.add_argument('folder');m.add_argument('capture_map',type=Path)
    a=p.parse_args();r=generate(a.folder,a.rate,a.seconds) if a.action=='generate' else compare_files(a.folder,json.loads(a.capture_map.read_text()));print(json.dumps(r,indent=2,allow_nan=False))
