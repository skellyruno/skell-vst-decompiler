"""Test a fixed -12 dB output trim on explicitly selected private vocal inputs.
This is a full-wet lab configuration, not a new processor or production default.
Keep the manifest, individual results and recordings private.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import soundfile as sf
from owned_private_vocal import ROOT, CONFIGS, estimate_peak, db, rms


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=[];gain=10**(-12/20)
    with tempfile.TemporaryDirectory(prefix='skell-headroom-') as d:
        path=Path(d)/'headroom.so'
        subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror',str(ROOT/'tests/fixtures/owned_color_headroom.cpp'),'-o',str(path)],check=True)
        lib=C.CDLL(str(path));fn=lib.render_color_gain;ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS')
        fn.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];fn.restype=C.c_int
        for item in json.loads(a.manifest.read_text())['inputs']:
            src=Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256']:raise ValueError('Input fingerprint mismatch')
            x,fs=sf.read(src,dtype='float64',always_2d=True)
            if x.shape[1] not in (1,2) or not 8000<=fs<=384000 or not np.isfinite(x).all() or not len(x) or rms(x)<=1e-12:raise ValueError('Unsupported or silent input')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            results={}
            for k,(name,_,delay) in enumerate(CONFIGS[2:]):
                inp=np.ascontiguousarray(np.pad(x,((0,delay),(0,0))));base=np.empty_like(inp);out=np.empty_like(inp)
                if fn(k,fs,0,inp,base,len(inp))!=1 or fn(k,fs,-12,inp,out,len(inp))!=1:raise RuntimeError('Native render failed')
                if not np.isfinite(base).all() or not np.isfinite(out).all():raise RuntimeError('Nonfinite render')
                err=float(np.max(np.abs(out-base*gain)))
                if err>1e-12:raise RuntimeError('Gain-only behavior failed')
                orig=base[delay:delay+len(x)];y=out[delay:delay+len(x)]
                results[name]={'waveform_scale_max_error':err,'before_peak_est_dbfs':db(estimate_peak(orig)),
                               'after_peak_est_dbfs':db(estimate_peak(y)),'after_rms_gain_db':db(rms(y)/rms(x)),
                               'after_samples_over_full_scale':int(np.count_nonzero(np.abs(y)>1))}
            rows.append({'id':item['id'],'stage':item['stage'],'fs':fs,'source_sha256':digest,'metrics':results})
            print(item['id'],flush=True)
        binary_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    a.output.write_text(json.dumps({'schema':1,'trim_db':-12,'native_sha256':binary_sha,'inputs':rows,'limits':'Full-wet original lab configurations; -12 dB fixed output trim, not a limiter, AGC or production setting. Peak estimated using 4x polyphase interpolation. No universal headroom guarantee.'},indent=2)+'\n')

if __name__=='__main__':main()
