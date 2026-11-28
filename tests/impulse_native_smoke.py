"""Real built-in native delay controls, not vendor-reference execution."""
import json
import numpy as np
import pedalboard as pb
from skell_vst_decompiler.impulse_calibration import inspect_impulse


def main():
    assert pb.__version__=='0.9.23'
    rows=[]
    for fs in (44100,48000,96000):
        n=fs//4+13;x=np.zeros((n,2),np.float32);x[7,1]=.5
        outputs=[]
        for block in (64,1024):
            fx=pb.Delay(delay_seconds=.01,feedback=.5,mix=1)
            y=fx.process(x.T.copy(),fs,buffer_size=block,reset=True).T
            r=inspect_impulse(x,y,fs);p=r['outputs'][1];delay=p['first_arrival_samples']
            assert abs(delay-.01*fs)<=1 and r['outputs'][0]['first_arrival_samples'] is None
            assert len(p['echo_peaks'])>=4
            for i,e in enumerate(p['echo_peaks'][:4],1):
                assert e['offset_samples']==delay*i and abs(e['gain']-.5**(i-1))<1e-6
            a=fx.process(x[:64].T.copy(),fs,buffer_size=block,reset=True).T
            b=fx.process(x[64:].T.copy(),fs,buffer_size=block,reset=False).T
            err=float(np.max(abs(np.concatenate([a,b])-y)));assert err==0
            z=fx.process(np.zeros((2,n),np.float32),fs,buffer_size=block,reset=True)
            reset_peak=float(np.max(abs(z)));assert reset_peak==0
            outputs.append(y)
            rows.append({'sample_rate':fs,'block_size':block,'frames':n,'first_arrival_samples':delay,'echo_peaks':p['echo_peaks'][:4],'split_error':err,'reset_peak':reset_peak})
        assert np.array_equal(*outputs)
    print('SKELL_IMPULSE_NATIVE_RESULT '+json.dumps(rows,sort_keys=True))


if __name__=='__main__':main()
