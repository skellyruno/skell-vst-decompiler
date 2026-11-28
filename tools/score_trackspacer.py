"""Score aligned synthetic reference renders, not vendor source or listening parity."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf

RATE = 48000
GROUPS = {'level': (6, [1000]), 'frequency': (5, [20,30,100,1000,9000]), 'stereo': (4, [1000])}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audio(path, count, offset=0):
    if type(offset) is not int or not 0 <= offset <= RATE:
        raise ValueError('Explicit offset must be an integer 0..48000')
    info=sf.info(path)
    if info.samplerate != RATE or info.channels != 2 or info.frames != count+offset or info.subtype not in ('PCM_24','PCM_32','FLOAT','DOUBLE'):
        raise ValueError(f'Unexpected render format/length: {path.name}')
    x, _=sf.read(path,dtype='float64',always_2d=True)
    if not np.isfinite(x).all(): raise ValueError('Nonfinite audio')
    return x[offset:]

def tone_amplitude(x,hz):
    phase=2*np.pi*hz*np.arange(len(x))/RATE
    return 2*np.abs(np.exp(-1j*phase)@x)/len(x)

def score(root):
    root=Path(root)
    m=json.loads((root/'manifest.json').read_text())
    if m.get('sample_rate')!=RATE or m.get('segment_seconds')!=3 or m.get('steady_analysis_interval_seconds')!=[1,2]:
        raise ValueError('Wrong probe manifest')
    meta=json.loads((root/'render_metadata.json').read_text())
    rows=[]
    for group,(segments,tones) in GROUPS.items():
        count=segments*3*RATE
        for role in ('main','key'):
            p=root/f'{group}_{role}.wav'
            if sha(p)!=m['source_sha256'][p.name]:raise ValueError('Probe fingerprint mismatch')
        dry=audio(root/f'{group}_main.wav',count)
        baseline=audio(root/f'bypass_{group}.wav',count,meta['bypass'][group])
        if np.max(np.abs(dry-baseline))>2e-6:raise ValueError('Bypass differs from known input; verify alignment and gain')
        wet={}
        for name in ('original','skell'):
            path=root/f'{name}_{group}.wav';record=meta[name][group]
            if not record['version'] or not record['settings'] or sha(path)!=record['sha256']:
                raise ValueError('Render metadata/fingerprint missing or mismatched')
            wet[name]=audio(path,count,record['offset_samples'])
        for i in range(segments):
            span=slice((3*i+1)*RATE,(3*i+2)*RATE)
            for f in tones:
                d=tone_amplitude(baseline[span],f)
                if np.any(d<1e-5):raise ValueError('Probe tone missing')
                cuts={name:-20*np.log10(np.maximum(tone_amplitude(x[span],f)/d,1e-12)) for name,x in wet.items()}
                rows.append(dict(group=group,segment=i,frequency_hz=f,original_cut_db=cuts['original'].tolist(),skell_cut_db=cuts['skell'].tolist(),difference_db=(cuts['skell']-cuts['original']).tolist()))
    delta=np.array([r['difference_db'] for r in rows]);return {'rows':rows,'mean_absolute_cut_error_db':float(np.mean(np.abs(delta))),'max_absolute_cut_error_db':float(np.max(np.abs(delta))),'limits':'Synthetic steady tone attenuation only; not full phase, attack/release, listening, vendor identity or DSP completeness. Operator-provided versions/settings and offsets are not independently authenticated.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory');a=p.parse_args();print(json.dumps(score(a.directory),indent=2,allow_nan=False))
