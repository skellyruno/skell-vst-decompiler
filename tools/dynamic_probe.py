"""Generate and score a synchronized two-way frequency-ducking transient probe."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf

FS=48000
N=6*FS
WIN=480
TONES=(100,1000,9000)
BURSTS=((100,200),(300,400))  # 10ms blocks

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def generate(root):
    root=Path(root)
    root.mkdir(parents=True,exist_ok=False)
    t=np.arange(N)/FS
    main=sum(.08*np.sin(2*np.pi*f*t) for f in TONES)
    key=np.zeros(N)
    for (a,b),amp in zip(BURSTS,(.4,.1)):
        k=np.arange((b-a)*WIN)/FS
        key[a*WIN:b*WIN]=amp*np.sin(2*np.pi*1000*k)
    for name,x in [('main',main),('key',key)]:
        sf.write(root/f'{name}.wav',np.column_stack([x,x]),FS,subtype='PCM_24')
    meta={'schema':1,'sample_rate':FS,'frames':N,'window_samples':WIN,'frequencies_hz':list(TONES),'bursts_blocks':[list(b) for b in BURSTS], 'source_sha256':{name:sha(root/f'{name}.wav') for name in ('main','key')}}
    (root/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    template={k:{'offset_samples':0,'sha256':'','settings':'','version':''} for k in ('bypass','original','skell')}
    (root/'render_metadata.template.json').write_text(json.dumps(template,indent=2)+'\n')

def read(root,name,offset=0):
    if type(offset) is not int or not 0<=offset<=FS:
        raise ValueError('explicit offset must be integer 0..48000')
    p=root/f'{name}.wav'
    i=sf.info(p)
    if i.samplerate!=FS or i.frames!=N+offset or i.channels!=2 or i.subtype not in ('PCM_24','PCM_32','FLOAT','DOUBLE'):
        raise ValueError(f'invalid format or frame count: {name}')
    x,_=sf.read(p,dtype='float64',always_2d=True)
    if not np.isfinite(x).all():raise ValueError('nonfinite render')
    return x[offset:]

def amplitudes(x):
    # All probe tones complete an integer number of cycles in each 10ms block.
    blocks=x.reshape(-1,WIN,2)
    basis=np.exp(-2j*np.pi*np.outer(np.arange(WIN)/FS,TONES))
    return 2*np.abs(np.einsum('bwc,wf->bfc',blocks,basis))/WIN

def first(mask):
    indices=np.flatnonzero(mask)
    return None if not len(indices) else int(indices[0])*10

def summarize(cut):
    rows=[]
    for idx,(a,b) in enumerate(BURSTS):
        # Last 200ms of key-on; no attack or release estimate for weak cuts.
        for j,f in enumerate(TONES):
            for c in range(2):
                v=cut[:,j,c]
                base=float(np.median(v[a-20:a]));steady=float(np.median(v[b-20:b])-base)
                attack=release=None
                if steady>=.5:
                    attack=first(v[a:b]-base>=.632*steady)
                    release=first(v[b:b+100]-base<=.1*steady)
                rows.append(dict(burst=idx,frequency_hz=f,channel=c,baseline_cut_db=base,steady_delta_db=steady,attack_63pct_ms=attack,recovery_10pct_ms=release))
    return rows

def score(root):
    root=Path(root);m=json.loads((root/'manifest.json').read_text())
    expected=(m.get('schema'),m.get('sample_rate'),m.get('frames'),m.get('window_samples'),m.get('frequencies_hz'),m.get('bursts_blocks'))
    if expected!=(1,FS,N,WIN,list(TONES),[list(b) for b in BURSTS]):raise ValueError('probe manifest mismatch')
    for name in ('main','key'):
        if sha(root/f'{name}.wav')!=m['source_sha256'][name]:raise ValueError('source hash mismatch')
        read(root,name)
    meta=json.loads((root/'render_metadata.json').read_text());renders={}
    for name in ('bypass','original','skell'):
        r=meta[name]
        if not r['version'] or not r['settings'] or sha(root/f'{name}.wav')!=r['sha256']:
            raise ValueError('missing version/settings or render hash mismatch')
        renders[name]=read(root,name,r['offset_samples'])
    if np.max(np.abs(renders['bypass']-read(root,'main')))>2e-6:raise ValueError('bypass identity/gain mismatch')
    d=amplitudes(renders['bypass'])
    if np.any(d<.01):raise ValueError('missing probe tone')
    curves={name:-20*np.log10(np.maximum(amplitudes(renders[name])/d,1e-12)) for name in ('original','skell')}
    return {'original':summarize(curves['original']),'skell':summarize(curves['skell']), 'mean_absolute_curve_difference_db':float(np.mean(np.abs(curves['original']-curves['skell']))),'limits':'10ms block estimates, not fitted time constants. Operator-supplied alignment/settings; time-varying spectral leakage possible; no listening or vendor identity certification.'}

def selftest():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/'kit';generate(root);dry=read(root,'main');meta={}
        for name in ('bypass','original','skell'):
            y=dry.copy()
            if name!='bypass':
                delay=4 if name=='original' else 7
                y[(100+delay)*WIN:(200+8)*WIN]*=.5
                y[(300+delay)*WIN:(400+8)*WIN]*=.75
            sf.write(root/f'{name}.wav',y,FS,subtype='FLOAT')
            meta[name]={'offset_samples':0,'sha256':sha(root/f'{name}.wav'),'version':'owned synthetic','settings':'known step gain'}
        (root/'render_metadata.json').write_text(json.dumps(meta))
        r=score(root)
        assert len(r['original'])==12 and len(r['skell'])==12
        for a,b in zip(r['original'],r['skell']):
            assert abs(a['steady_delta_db']-(-20*np.log10(.5 if a['burst']==0 else .75)))<1e-5
            assert a['attack_63pct_ms']==40 and b['attack_63pct_ms']==70
            assert a['recovery_10pct_ms']==b['recovery_10pct_ms']==80
        sf.write(root/'bypass.wav',dry*.9,FS,subtype='FLOAT');meta['bypass']['sha256']=sha(root/'bypass.wav');(root/'render_metadata.json').write_text(json.dumps(meta))
        try:score(root)
        except ValueError as e:assert 'bypass identity' in str(e)
        else:raise AssertionError('bad bypass accepted')
        print('24 channel/frequency/burst rows; 40/70ms onset, 80ms recovery; bad bypass rejected: PASS')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['generate','score','selftest']);p.add_argument('directory',nargs='?');a=p.parse_args()
    if a.action=='selftest':selftest()
    elif a.action=='generate':generate(a.directory)
    else:print(json.dumps(score(a.directory),indent=2,allow_nan=False))
