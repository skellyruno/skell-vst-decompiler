"""Compile/run original engine variants; no vendor binary or private audio."""
import json
import pathlib
import subprocess
import sys
import numpy as np
from skell_vst_decompiler.spectral_probe import measure


def run(executable):
    result = []
    for fs in (44100, 48000, 96000, 192000):
        rate = {'sample_rate': fs}
        for kind in ('baseline', 'candidate'):
            raw = subprocess.check_output([executable, kind, str(fs)])
            vals = np.frombuffer(raw, dtype='<f4').reshape(3, fs, 4)
            rows = [measure(fs, (100, 1000, 9000), v[:, :2], v[:, 2:]) for v in vals]
            gains = [[v['channels'][0]['gain_db'] for v in row['tones']] for row in rows]
            right = [[v['channels'][1]['gain_db'] for v in row['tones']] for row in rows]
            assert np.max(np.abs(right)) < 1e-6, (fs, kind, right)
            if kind == 'candidate':
                for i in range(3):
                    assert gains[i][i] < -4.5, (fs, gains)
                    assert max(abs(gains[i][j]) for j in range(3) if i != j) < .35, (fs, gains)
            rate[kind] = {'left_gain_db': gains, 'right_gain_db': right,
                          'left_residual_rms': [v['processed_residual_rms'][0] for v in rows]}
        result.append(rate)
    return result

if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('usage: spacer_selectivity_smoke.py /path/to/native_comparison')
    print(json.dumps(run(sys.argv[1]), indent=2, allow_nan=False))
