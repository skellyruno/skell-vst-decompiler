"""Independent coherent-tone measurements of aligned, externally rendered audio.

No plugin loading, auto-alignment, or inference of internal implementation.
"""
import numpy as np


def probe(fs, frequencies):
    """One-second stereo dual-mono multitone, bounded and phase coherent."""
    if type(fs) is not int or not 8000 <= fs <= 192000:
        raise ValueError('invalid sample rate')
    f = tuple(frequencies)
    if not 1 <= len(f) <= 32 or any(type(v) is not int or not 20 <= v < fs / 2 for v in f) or len(set(f)) != len(f):
        raise ValueError('expected distinct integer-Hz tones below Nyquist')
    t = np.arange(fs) / fs
    x = sum(np.sin(2 * np.pi * v * t) for v in f) * (.5 / len(f))
    return np.column_stack((x, x))


def measure(fs, frequencies, baseline, processed):
    """Compare one-second steady-state windows; return per-channel complex gain.

    Baseline is an aligned detector-off render, not necessarily the dry input.
    Residual is energy outside the selected tones, not a distortion-only metric.
    Silence at a reference tone yields None rather than a misleading dB value.
    """
    f = tuple(frequencies)
    probe(fs, f)
    a, b = (np.asarray(v, dtype=float) for v in (baseline, processed))
    if any(v.shape != (fs, 2) or not np.isfinite(v).all() for v in (a, b)):
        raise ValueError('expected finite, aligned one-second stereo windows')
    A, B = (np.fft.rfft(v, axis=0) * (2. / fs) for v in (a, b))
    rows = []
    for hz in f:
        channels = []
        for ch in range(2):
            ref, out = A[hz, ch], B[hz, ch]
            gain = out / ref if abs(ref) >= 1e-8 else None
            channels.append(None if gain is None else {
                'gain_db': float(20 * np.log10(max(abs(gain), 1e-12))),
                'phase_deg': float(np.angle(gain, deg=True)) if abs(gain) >= 1e-12 else None})
        rows.append({'hz': hz, 'channels': channels})
    def residual(v, spectrum):
        filtered = np.zeros_like(spectrum)
        filtered[list(f)] = spectrum[list(f)] * (fs / 2.)
        r = v - np.fft.irfft(filtered, n=fs, axis=0)
        return [float(x) for x in np.sqrt(np.mean(r * r, axis=0))]
    return {'tones': rows, 'baseline_residual_rms': residual(a, A),
            'processed_residual_rms': residual(b, B)}
