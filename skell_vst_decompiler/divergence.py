"""Local diagnostic for already aligned reference/model samples; no alignment inference."""
import math
import numpy as np


def first_difference(reference, candidate, fs, *, atol=1e-6, rtol=1e-5, block=256):
    """Find the earliest tolerance violation; report indices and aggregate errors only.

    The reference sets the relative tolerance. Numerical equality is not bitwise
    equality or evidence of internal algorithm identity. Never adjusts gain or delay.
    """
    if type(fs) is not int or not 8000 <= fs <= 192000 or type(block) is not int or not 1 <= block <= 65536:
        raise ValueError('Invalid sample rate or block size')
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in (atol, rtol)):
        raise ValueError('Invalid tolerance')
    a,b = np.asarray(reference,dtype=np.float64),np.asarray(candidate,dtype=np.float64)
    if a.ndim != 2 or a.shape != b.shape or a.shape[1] not in (1,2) or not 1 <= len(a) <= 120*fs:
        raise ValueError('Expected matched aligned mono/stereo arrays')
    first=None; bad_frames=bad_samples=0; peak=energy=0.; ref_energy=0.
    for start in range(0,len(a),block):
        r,c=a[start:start+block],b[start:start+block]
        if not np.all(np.isfinite(r)) or not np.all(np.isfinite(c)) or max(np.max(abs(r)),np.max(abs(c)))>64:
            raise ValueError('Invalid audio samples')
        err=np.abs(c-r); mask=err>atol+rtol*np.abs(r)
        bad_frames+=int(np.count_nonzero(np.any(mask,axis=1)))
        bad_samples+=int(np.count_nonzero(mask))
        if first is None and np.any(mask):
            frame,channel=map(int,np.argwhere(mask)[0]);first={'sample_index':start+frame,'channel_index':channel,'seconds':(start+frame)/fs,'block_index':start//block,'block_start_sample':start}
        peak=max(peak,float(err.max()));energy+=float(np.sum(err*err));ref_energy+=float(np.sum(r*r))
    return {'frames':len(a),'channels':a.shape[1],'sample_rate':fs,'block_size':block,'absolute_tolerance':atol,'relative_tolerance':rtol,'first_difference':first,'mismatched_frames':bad_frames,'mismatched_samples':bad_samples,'max_absolute_error':peak,'rms_error':math.sqrt(energy/a.size),'relative_residual_db':20*math.log10(max(math.sqrt(energy/ref_energy),1e-15)) if ref_energy>0 else None,'note':'Aligned output comparison only; no internal state inference or listening approval.'}
