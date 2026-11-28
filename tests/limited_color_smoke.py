"""Owned chain tests, sample peak guarantee and non-certified intersample estimate."""
import json,subprocess,sys
import numpy as np
from scipy.signal import resample_poly

def run(exe):
    report=[]
    for fs in (44100,48000,96000,192000):
        latency=40+round(fs*.003)
        impulse=np.frombuffer(subprocess.check_output([exe,'impulse',str(fs),'-1.5']),'<f4').reshape(-1,8)
        assert np.flatnonzero(impulse[:,6]).tolist()==[latency] and abs(impulse[latency,6]-.1)<1e-7 and not impulse[:,7].any()
        out=np.frombuffer(subprocess.check_output([exe,'synthetic',str(fs),'-1.5']),'<f4').reshape(-1,8)
        assert out.shape==(2*fs+latency,8) and np.isfinite(out).all()
        s=out[latency:latency+2*fs,6:]; assert np.max(np.abs(s))<=10**(-1.5/20)+1e-7
        report.append({'fs':fs,'delay_samples':latency,'delay_ms':latency*1000/fs,'sample_peak':float(np.max(np.abs(s))),'estimated_4x_peak':float(np.max(np.abs(resample_poly(s.astype(float),4,1,axis=0)))),'color_sample_peak':float(np.max(np.abs(out[:,4:6]))),'rms':float(np.sqrt(np.mean(s.astype(float)**2)))})
    return report
if __name__=='__main__':print(json.dumps(run(sys.argv[1]),indent=2,allow_nan=False))
