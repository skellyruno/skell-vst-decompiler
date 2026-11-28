"""Generate original stereo topology probes compatible with host_capture manifests."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf


def generate(folder, fs=48000):
    if fs not in (44100, 48000, 96000):
        raise ValueError('unsupported sample rate')
    root=Path(folder);root.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(818);n=fs;shift=fs//20
    x=rng.uniform(-.4,.4,(n,2)).astype(np.float32)
    z=rng.uniform(-.3,.3,(n,2)).astype(np.float32)
    alternate=x.copy();alternate[:n//2]*=.1
    delayed=np.zeros_like(x);delayed[shift:]=x[:-shift]
    t=np.arange(2*fs)/fs;quiet=(.02*np.sin(2*np.pi*1000*t)).astype(np.float32)
    loud=(.8*np.sin(2*np.pi*400*t)).astype(np.float32)
    q=np.column_stack((quiet,np.zeros_like(quiet)));w=q.copy();w[:,1]=loud
    cases=[('base',x),('repeat',x),('half',.5*x),('other',z),('sum',x+z),('alternate_prefix',alternate),('shifted',delayed),('quiet_left',q),('loud_right',w),('quiet_right',q[:,::-1]),('loud_left',w[:,::-1])]
    rows=[]
    for key,a in cases:
        file=root/(key+'.wav');sf.write(file,a,fs,subtype='FLOAT')
        rows.append(dict(id=key,family='topology',file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),frames=len(a),channels=2,windows=[]))
    manifest=dict(schema=1,sample_rate=fs,cases=rows,suffix_start=n//2,shift_samples=shift,note='Render each separately from reset at identical settings; no normalization or alignment changes.')
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder');p.add_argument('--rate',type=int,default=48000);a=p.parse_args();generate(a.folder,a.rate)
