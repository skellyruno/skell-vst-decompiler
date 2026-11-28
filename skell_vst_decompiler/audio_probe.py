"""Coherent-tone PCM WAV analysis, with explicit provenance and alias-bin collisions.
Use an integer-Hz tone and a one-second steady-state window. The probe never loads a plugin.
Requires numpy and scipy (optional audio extras). WAV is an actual sample measurement;
provenance is caller-declared and not proof of a commercial plugin render.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def measure(path, tone_hz, start_seconds=1, source='unverified WAV provenance'):
    import numpy as np
    from scipy.io import wavfile
    path=Path(path)
    if not isinstance(tone_hz,int) or not isinstance(start_seconds,int) or start_seconds<0:
        raise ValueError('Use integer Hz and integer nonnegative window start')
    fs,raw=wavfile.read(path)
    if not 1<=tone_hz<fs/2:raise ValueError('Tone must be below Nyquist')
    if raw.dtype.kind=='u':
        half=2**(raw.dtype.itemsize*8-1); x=(raw.astype(np.float64)-half)/half
    elif raw.dtype.kind=='i':x=raw.astype(np.float64)/2**(raw.dtype.itemsize*8-1)
    elif raw.dtype.kind=='f':x=raw.astype(np.float64)
    else:raise ValueError('Unsupported PCM dtype')
    if x.ndim==1:x=x[:,None]
    if x.ndim!=2 or not 1<=x.shape[1]<=32 or not np.all(np.isfinite(x)):
        raise ValueError('Invalid audio data')
    n=int(fs); begin=start_seconds*n
    if begin+n>len(x):raise ValueError('Need full 1-second steady-state window')
    w=x[begin:begin+n]; out=[]
    bins={}; collisions=[]
    for order in range(2,16):
        f=order*tone_hz
        folded=abs((f+fs/2)%fs-fs/2)
        k=int(folded)
        bins.setdefault(k,[]).append({'order':order,'folded':f>=fs/2})
    def db(a):return float(20*np.log10(max(float(a),1e-15)))
    for c in range(w.shape[1]):
        y=w[:,c]; a=np.abs(np.fft.rfft(y))*2/n; a[0]*=.5
        if n%2==0:a[-1]*=.5
        fundamental=float(a[tone_hz]); valid_h=[]; valid_alias=[]; components=[]
        for k,orders in sorted(bins.items()):
            # Multiple orders, DC/Nyquist and fundamental coincidences cannot be attributed uniquely.
            ambiguous=len(orders)!=1 or k in (0,tone_hz) or k==fs/2
            kind='ambiguous' if ambiguous else 'alias_candidate' if orders[0]['folded'] else 'harmonic'
            if kind=='harmonic':valid_h.append(float(a[k]))
            if kind=='alias_candidate':valid_alias.append(float(a[k]))
            components.append({'frequency_hz':k,'orders':orders,'kind':kind,'dbfs':db(a[k]),'dbc':db(a[k]/max(fundamental,1e-15))})
        out.append({'channel':c,'fundamental_dbfs':db(fundamental),'peak_dbfs':db(np.max(np.abs(y))),
                    'rms_dbfs':db(np.sqrt(np.mean(y*y))),'dc':float(np.mean(y)),
                    'unambiguous_harmonic_power_dbc':db(math.sqrt(sum(v*v for v in valid_h))/max(fundamental,1e-15)) if valid_h else None,
                    'unambiguous_alias_candidate_power_dbc':db(math.sqrt(sum(v*v for v in valid_alias))/max(fundamental,1e-15)) if valid_alias else None,
                    'components':components})
    return {'source':source,'wav':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sample_rate':int(fs),'tone_hz':tone_hz,'window_start_seconds':start_seconds,'window_frames':n,'channels':out,
            'limits':'Actual PCM FFT, not a host or CPU benchmark. Folded bins are candidates: higher-order collisions, leakage, noise, modulation and resampler artifacts can contribute. Use a coherent isolated sine with no modulation. No complete THD+N claim.'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('wav',type=Path);p.add_argument('--tone',type=int,required=True);p.add_argument('--start',type=int,default=1);p.add_argument('--source',default='unverified WAV provenance');p.add_argument('--out',type=Path)
    a=p.parse_args(argv)
    if a.out and a.out.resolve()==a.wav.resolve():p.error('Output cannot overwrite input WAV')
    r=measure(a.wav,a.tone,a.start,a.source);s=json.dumps(r,indent=2,allow_nan=False)+'\n'
    if a.out:a.out.write_text(s)
    print(s,end='')
if __name__=='__main__':main()
