"""Compare independent historical-style and YIN-style F0 detectors on common inputs."""
import json
import math
from statistics import median
import numpy as np
from skell_vst_decompiler.historical_pitch_reference import estimate as historical
from skell_vst_decompiler.pitch_reference import estimate as yin


def main():
    rng=np.random.default_rng(125)
    summary={}
    for name,fn in [('two_period',historical),('yin_fft',lambda x,fs:yin(x,fs,backend='fft'))]:
        # Seed separately so every detector sees identical material.
        rng=np.random.default_rng(125)
        errors=[];rejected=0;gross=0;count=0
        for fs in (44100,48000,96000):
            t=np.arange(int(fs*.065))/fs
            for hz in (82.41,110.,220.,440.,880.):
                for noise in (0.,.05,.15):
                    for hs in ((1,2,3),(2,3,4)):
                        x=sum(np.sin(2*np.pi*hz*h*t)/h for h in hs)+rng.normal(0.,noise,len(t))
                        count+=1
                        f,c=fn(x,fs)
                        if f is None:
                            rejected+=1
                            continue
                        error=abs(1200*math.log2(f/hz));errors.append(error)
                        gross+=error>50.
        summary[name]={'cases':count,'accepted':len(errors),'rejected':rejected,
                       'gross_errors_over_50_cents':gross,
                       'median_abs_cents':median(errors) if errors else None,
                       'max_abs_cents':max(errors) if errors else None}
    print('SKELL_HISTORICAL_PITCH_RESULT '+json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
