"""Synthetic held-out sweep and owned chain measurements, not reference audio."""
import json, subprocess, sys
import numpy as np
from scipy.signal import resample_poly


def run(exe):
    out=[]
    for fs in (44100,48000,96000,192000):
        raw=subprocess.check_output([exe,'coverage',str(fs)],text=True)
        sweep=np.array([[float(v) for v in line.split()] for line in raw.splitlines()])
        assert len(sweep)==36 and np.isfinite(sweep).all()
        assert np.max(sweep[:,2])<1e-8
        core=sweep[(sweep[:,0]>=63)&(sweep[:,0]<=16000)]
        assert core[:,1].max()<-2.0, (fs,core[:,1].max())
        vals=np.frombuffer(subprocess.check_output([exe,'chain',str(fs)]),dtype='<f4').reshape(5,2*fs,4)
        metrics=[]
        for name,v in zip(('dry','presence','leveler','color','color_minus_3db'),vals):
            x=v[:,2:].astype(float);assert np.isfinite(x).all()
            metrics.append({'stage':name,'rms':float(np.sqrt(np.mean(x*x))),'sample_peak':float(np.max(np.abs(x))),'intersample_estimate_4x':float(np.max(np.abs(resample_poly(x,4,1,axis=0))))})
        assert metrics[-1]['sample_peak']<metrics[-2]['sample_peak']
        out.append({'fs':fs,'sweep_hz_db_right_error_projection':sweep.tolist(),'core_weakest_cut_db':float(core[:,1].max()),'chain':metrics})
    return out
if __name__=='__main__':print(json.dumps(run(sys.argv[1]),indent=2,allow_nan=False))
