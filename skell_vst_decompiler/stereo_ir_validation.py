"""Offline validation of authorized stereo impulse and held-out audio renders.

No automatic time alignment, gain fitting, or tail truncation. The measured
matrix is private in-memory data, not a vendor implementation or export.
"""
import numpy as np
from scipy.signal import fftconvolve


def _stereo(a, fs):
    a = np.asarray(a, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2 or not 1 <= len(a) <= 30 * fs:
        raise ValueError('expected bounded stereo audio')
    if not np.isfinite(a).all() or np.max(np.abs(a)) > 64:
        raise ValueError('invalid samples')
    return a


def _relative_error(reference, estimate):
    delta = np.linalg.norm(reference - estimate)
    norm = np.linalg.norm(reference)
    return float(delta / norm) if norm else (0.0 if delta == 0 else None)


def validate_stereo_ir(captures, probe, observed, fs, *, tolerance=1e-5):
    """Four or more (input, output) impulse pairs, both levels per input.

    Each impulse starts at a common index, with identical capture lengths.
    The held-out probe must include the entire convolution tail. Returns
    diagnostics only; finite captures cannot prove global LTI behavior.
    """
    if type(fs) is not int or not 8000 <= fs <= 192000:
        raise ValueError('invalid sample rate')
    if not np.isfinite(tolerance) or not 0 < tolerance <= .01:
        raise ValueError('invalid tolerance')
    if not 4 <= len(captures) <= 16:
        raise ValueError('four to sixteen captures required')
    groups = [[], []]
    shape = origin = None
    pre = 0.0
    for source, wet in captures:
        x, y = _stereo(source, fs), _stereo(wet, fs)
        if x.shape != y.shape or (shape is not None and x.shape != shape):
            raise ValueError('capture length mismatch')
        shape = x.shape
        nz = np.argwhere(x != 0)
        if len(nz) != 1:
            raise ValueError('exactly one impulse required')
        idx, ch = map(int, nz[0])
        amp = x[idx, ch]
        if not .01 <= abs(amp) <= 1 or (origin is not None and idx != origin):
            raise ValueError('invalid impulse level or origin')
        origin = idx
        if len(x) - idx < 64:
            raise ValueError('capture too short')
        if idx:
            pre = max(pre, float(np.max(np.abs(y[:idx] / amp))))
        groups[ch].append((abs(amp), y[idx:] / amp))
    responses = []
    errors = []
    for group in groups:
        if len(group) < 2 or max(a for a, _ in group) / min(a for a, _ in group) < 1.5:
            raise ValueError('two distinct levels required per input')
        # Lowest-level observation is the fixed reference, never a fitted mean.
        group.sort(key=lambda pair: pair[0])
        base = group[0][1]
        responses.append(base)
        errors.append([_relative_error(base, h) for _, h in group[1:]])
    probe, observed = _stereo(probe, fs), _stereo(observed, fs)
    n = len(probe) + len(responses[0]) - 1
    if len(observed) != n:
        raise ValueError('held-out output must include full captured tail')
    predicted = np.zeros_like(observed)
    paths = []
    for i, response in enumerate(responses):
        for o in range(2):
            h = response[:, o]
            predicted[:, o] += fftconvolve(probe[:, i], h)
            peak = float(np.max(np.abs(h)))
            active = np.flatnonzero(np.abs(h) > tolerance)
            energy = float(np.dot(h, h))
            tail = h[-max(1, len(h)//20):]
            paths.append({'input': i, 'output': o, 'first_arrival': int(active[0]) if len(active) else None,
                          'peak_gain': peak, 'last_5pct_energy_fraction': float(np.dot(tail, tail)/energy) if energy else 0.0})
    residual = _relative_error(observed, predicted)
    peak_error = float(np.max(np.abs(observed - predicted)))
    level_ok = all(e is not None and e <= tolerance for group in errors for e in group)
    excitation_ok = all(np.linalg.norm(probe[:, i]) > tolerance for i in range(2))
    output_ok = bool(np.linalg.norm(observed) > tolerance)
    tail_ok = all(p['last_5pct_energy_fraction'] <= tolerance**2 for p in paths)
    return {'sample_rate': fs, 'capture_frames': len(responses[0]), 'paths': paths,
            'level_relative_errors': errors, 'pre_input_peak': pre,
            'held_out_relative_error': residual, 'held_out_peak_error': peak_error,
            'level_consistent': bool(level_ok), 'both_inputs_excited': bool(excitation_ok),
            'capture_tail_quiet': bool(tail_ok), 'nonzero_output': output_ok,
            'passes_observed_gate': bool(level_ok and excitation_ok and output_ok and tail_ok and pre <= tolerance and residual is not None and residual <= tolerance and peak_error <= tolerance),
            'note': 'Finite observed conditions only; no timing/gain fitting, latency inference or vendor algorithm claim.'}
