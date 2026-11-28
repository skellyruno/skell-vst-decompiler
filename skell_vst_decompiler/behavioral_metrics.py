"""Independent render metrics; no inference of a vendor's implementation.
All inputs are aligned, finite, caller-authorized samples. No plugin loading.
"""
import numpy as np


def _stereo(x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 2 or not 1 <= len(x) <= 1920000 or not np.isfinite(x).all():
        raise ValueError('expected bounded finite stereo audio')
    return x


def _rate(fs):
    if type(fs) is not int or not 8000 <= fs <= 192000:
        raise ValueError('invalid sample rate')


def block_gain(fs, baseline, render, block_ms=10):
    """Per-channel least-squares scalar gain, and unexplained RMS residual.
    A scalar model cannot explain filter phase, modulation or distortion.
    Drop only the incomplete final block and report its size.
    """
    _rate(fs)
    a, b = _stereo(baseline), _stereo(render)
    if a.shape != b.shape or not np.isfinite(block_ms) or not 1 <= block_ms <= 1000:
        raise ValueError('invalid alignment or block duration')
    n = round(fs * block_ms / 1000)
    count = len(a) // n
    if not count:
        raise ValueError('no complete blocks')
    a, b = (v[:count*n].reshape(count, n, 2) for v in (a, b))
    power = np.mean(a*a, axis=1)
    valid = power >= 1e-12
    gain = np.divide(np.mean(a*b, axis=1), power, out=np.zeros_like(power), where=valid)
    residual = np.sqrt(np.mean((b-a*gain[:,None,:])**2, axis=1))
    return {'block_samples': n, 'discarded_samples': len(baseline)-count*n,
            'time_ms': ((np.arange(count)+.5)*n*1000/fs).tolist(),
            'gain': [[float(g) if ok else None for g,ok in zip(row,mask)] for row,mask in zip(gain,valid)],
            'residual_rms': residual.tolist()}


def tone_products(fs, hz, render, max_order=12):
    """One-second coherent harmonic spectrum; explicitly separate fold candidates.
    Fold collisions and non-harmonic bins cannot prove alias provenance.
    """
    _rate(fs)
    x = _stereo(render)
    if len(x) != fs or type(hz) is not int or not 20 <= hz < fs/2 or type(max_order) is not int or not 2 <= max_order <= 64:
        raise ValueError('expected one second and a coherent integer-Hz fundamental')
    spectrum = np.abs(np.fft.rfft(x, axis=0)) * (2/fs)
    spectrum[0] *= .5
    if fs%2 == 0:
        spectrum[-1] *= .5
    groups = {}
    for n in range(1, max_order+1):
        f = n*hz
        fold = min(f%fs, (-f)%fs)
        groups.setdefault(fold, []).append({'order':n, 'fold_candidate':f>fs/2})
    return [{'hz':f, 'origins':origins, 'ambiguous':len(origins)>1,
             'amplitude':spectrum[f].tolist()} for f,origins in sorted(groups.items())]


def sidebands(fs, carrier_hz, modulation_hz, render, orders=4):
    """One-second coherent modulation sidebands; not a delay-depth estimator."""
    _rate(fs)
    x = _stereo(render)
    if len(x)!=fs or any(type(v) is not int for v in (carrier_hz,modulation_hz,orders)) or not 1<=orders<=16 or modulation_hz<1 or carrier_hz-orders*modulation_hz<1 or carrier_hz+orders*modulation_hz>=fs/2:
        raise ValueError('invalid coherent sideband grid')
    A = np.fft.rfft(x,axis=0)*2/fs
    return [{'order':k,'hz':carrier_hz+k*modulation_hz,
             'amplitude':np.abs(A[carrier_hz+k*modulation_hz]).tolist()}
            for k in range(-orders,orders+1)]
