"""Cross-optimization render comparison: finite, equal shape, bounded numeric error."""
import sys
import numpy as np

def compare(a,b):
    a,b=map(lambda p:np.fromfile(p,dtype='<f4'),(a,b))
    if not len(a) or a.shape!=b.shape or len(a)%4 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('invalid chain capture')
    delta=np.abs(a.astype(float)-b.astype(float))
    peak=float(delta.max());rms=float(np.sqrt(np.mean(delta*delta)))
    if peak>2e-7 or rms>2e-8:
        raise AssertionError(f'chain render mismatch: peak={peak:.9g}, rms={rms:.9g}')
    return peak,rms
if __name__=='__main__':print('peak/rms render error',compare(*sys.argv[1:]))
