"""Reproducible synthetic measurements; not real vocal or plugin tests."""
import json
import math
from statistics import median
from time import perf_counter
import numpy as np
from skell_vst_decompiler.pitch_reference import estimate
from skell_vst_decompiler.saturation_reference import saturate


def main():
    frames=[]
    rng=np.random.default_rng(22)
    for fs in (44100,48000,96000):
        t=np.arange(int(fs*.065))/fs
        for hz in (82.41,110.,220.,440.,880.):
            for noise in (0.,.05):
                x=sum(np.sin(2*np.pi*hz*h*t)/h for h in (1,2,3))+rng.normal(0.,noise,len(t))
                frames.append((x,fs,hz))
    times={}
    results={}
    for backend in ('direct','fft'):
        durations=[]
        for _ in range(3):
            start=perf_counter()
            results[backend]=[estimate(x,fs,backend=backend) for x,fs,_ in frames]
            durations.append(perf_counter()-start)
        times[backend]=median(durations)
    errors=[]
    for (_,_,hz),a,b in zip(frames,results['direct'],results['fft']):
        if a[0] is None or b[0] is None or abs(a[0]-b[0])>1e-7:
            raise RuntimeError('Detector parity failed')
        errors.append(abs(1200*math.log2(b[0]/hz)))
    if max(errors)>5:
        raise RuntimeError('Synthetic pitch accuracy regression')
    # Coherent 9 kHz sine, at 48 kHz. In-band fundamental excluded; other
    # bins include legitimate harmonics AND aliases, not alias-only energy.
    fs=48000;n=48000;freq=9000
    t=np.arange(n+1)/fs;x=.9*np.sin(2*np.pi*freq*t)
    powers={}
    for aa in (False,True):
        y=saturate(x,4.,antialias=aa)[1:]
        spec=np.abs(np.fft.rfft(y))**2
        fundamental=spec[freq]
        # Third harmonic aliases to 21 kHz; higher harmonics may share bins.
        powers[str(aa)]={'folded_21khz_relative_db':float(10*np.log10(max(spec[21000],1e-30)/fundamental)),
                         'fundamental_rms':float(np.sqrt(2*fundamental)/n)}
    print('SKELL_DSP_REFERENCE_RESULT '+json.dumps({'pitch_cases':len(frames),'max_absolute_cents':max(errors),
          'median_absolute_cents':median(errors),'median_batch_seconds':times,
          'speedup':times['direct']/times['fft'],'saturation_9khz':powers,
          'scope':'synthetic offline only; folded bin is not a full alias metric'},sort_keys=True))


if __name__=='__main__':main()
