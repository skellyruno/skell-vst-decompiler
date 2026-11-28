"""Original standalone probe bank for offline, authorized reference measurements."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf

RATES = (44100, 48000, 96000)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()


def probes(fs, tail_seconds=12):
    if type(fs) is not int or fs not in RATES or type(tail_seconds) is not int or not 2 <= tail_seconds <= 30:
        raise ValueError('unsupported rate or tail duration')
    origin = fs // 4
    for ch in range(2):
        for label, amp in [('low', .125), ('high', -.5)]:
            x = np.zeros((origin + tail_seconds * fs, 2), np.float32)
            x[origin, ch] = amp
            yield f'ir_{ch}_{label}', 'spatial', x, []
    # Broadband holdout has both independent inputs and the entire declared tail.
    rng = np.random.default_rng(4107)
    x = np.zeros((fs + tail_seconds * fs - 1, 2), np.float32)
    x[:fs] = rng.uniform(-.15, .15, (fs, 2))
    yield 'ir_holdout', 'spatial', x, []
    # Coherent windows avoid spectral leakage. Isolate channels rather than assuming symmetry.
    t = np.arange(fs) / fs
    for ch in range(2):
        for level in (-36, -6):
            for freq in (80, 1000, 8000):
                x = np.zeros((2 * fs, 2), np.float32)
                x[:fs, ch] = 10**(level/20)*np.sin(2*np.pi*freq*t)
                yield f'tone_{ch}_{abs(level)}_{freq}', 'eq_color_dynamics', x, [{'start':fs//2,'stop':fs,'level_dbfs_peak':level}]
    # Different bass/high-frequency energy while total peak remains comparable.
    for freq in (80, 1000, 8000):
        n = 4*fs; x = np.zeros((n, 2), np.float32)
        level = np.repeat([.015, .5, .015, 0.], fs)
        phase = 2*np.pi*freq*np.arange(n)/fs
        x[:,0] = level*np.sin(phase); x[:,1] = .1*np.sin(phase)
        x[-fs:,1] = 0
        yield f'link_{freq}', 'dynamics', x, []
    # Detuning and silence alternate; includes an independent noise-only segment.
    n=4*fs; f=np.repeat([217., 231., 192., 0.],fs)
    phase=2*np.pi*np.cumsum(f)/fs
    mono=sum(.15/k*np.sin(k*phase) for k in range(1,5)); mono[-fs:]=rng.uniform(-.02,.02,fs)
    yield 'pitch_detune_noise', 'pitch', np.column_stack((mono,mono)).astype(np.float32), []


def generate(root, fs=48000, tail_seconds=12):
    root=Path(root); root.mkdir(parents=True,exist_ok=False); cases=[]
    for key,family,x,windows in probes(fs,tail_seconds):
        path=root/(key+'.wav'); sf.write(path,x,fs,subtype='FLOAT')
        cases.append({'id':key,'family':family,'file':path.name,'sha256':digest(path),'frames':len(x),'channels':2,'windows':windows})
    manifest={'schema':1,'sample_rate':fs,'cases':cases,'note':'Original synthetic stimuli; reset each render, preserve exact length, do not normalize. IR origin fs//4; holdout excitation first second. Tail energy must be verified.'}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('folder'); p.add_argument('--rate',type=int,default=48000); p.add_argument('--tail-seconds',type=int,default=12)
    a=p.parse_args(); print(json.dumps(generate(a.folder,a.rate,a.tail_seconds),indent=2))


if __name__=='__main__':main()
