"""Render original C++ offline prototypes on a privately supplied audio file.
Produces equal-length latency-aligned WAVs; never runs a vendor plugin.
"""
import argparse, hashlib, json, math, subprocess, tempfile
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, butter, sosfilt


def read_audio(path):
    import soundfile as sf
    x,fs=sf.read(path,dtype='float64')
    if x.ndim==1:x=np.repeat(x[:,None],2,axis=1)
    if x.ndim!=2 or x.shape[1]!=2 or not np.all(np.isfinite(x)) or not 8000<=fs<=384000:raise ValueError('Expected finite mono/stereo WAV')
    return fs,x


def db(v): return 20*math.log10(max(float(v),1e-15))
def metrics(x,fs):
    return {'sample_peak_dbfs':db(np.max(np.abs(x))),'estimated_4x_peak_dbfs':db(np.max(np.abs(resample_poly(x,4,1,axis=0)))),'rms_dbfs':db(np.sqrt(np.mean(x*x))),'dc_max':float(np.max(np.abs(np.mean(x,axis=0)))),'peak_frames_over_minus1_dbfs':int(np.count_nonzero(np.max(np.abs(x),axis=1)>10**(-1/20)+1e-7)),'difference_rms_dbfs':db(np.sqrt(np.mean(np.diff(x,axis=0)**2))), 'band_rms_dbfs':{f'{lo}-{hi}':db(np.sqrt(np.mean(sosfilt(butter(3,[lo,hi],btype='bandpass',fs=fs,output='sos'),x,axis=0)**2))) for lo,hi in [(150,400),(1000,4000),(6000,10000)] if hi<fs/2}}


def render(source,out,renderer,seconds=12):
    source,out,renderer=Path(source),Path(out),Path(renderer)
    if not 1<=seconds<=30:raise ValueError('Use 1..30 seconds')
    fs,a=read_audio(source);n=seconds*fs
    if len(a)<n:raise ValueError('Audio shorter than requested excerpt')
    # Deterministic loudest nonoverlapping window of the recording; same excerpt for all tests.
    windows=len(a)//n; index=max(range(windows),key=lambda i:float(np.mean(a[i*n:(i+1)*n]**2)))
    dry=a[index*n:(index+1)*n].copy(); drive=dry*10**(6/20)
    out.mkdir(parents=True,exist_ok=True)
    result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source':'user-provided music recording (not a dry vocal or commercial-plugin render)','sample_rate':fs,'start_seconds':index*seconds,'duration_seconds':seconds,'input_drive_db':6,'ceiling_dbfs':-1,'oversampled_internal_ceiling_dbfs':-1.25,'measurement_notes':'4x polyphase estimated peak, not certified dBTP. RMS and first-difference RMS are descriptive, not perceptual quality. Lookahead latency removed for offline comparison. No gain normalization on primary WAVs.','renders':{}}
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        for name,x in [('dry',dry),('driven',drive)]:
            y=x.astype(np.float32);wavfile.write(out/(name+'.wav'),fs,y);result['renders'][name]=metrics(y.astype(float),fs)
        for mode,x in [('baseline',drive),('lookahead',drive),('static_bell',dry),('bell',dry),('lookahead_margin',drive)]:
            raw=tmp/'in.raw';wet=tmp/'out.raw';factor=4 if mode=='lookahead_margin' else 1
            src=resample_poly(x,factor,1,axis=0) if factor>1 else x;src.astype('<f4').tofile(raw)
            run=subprocess.run([str(renderer.resolve()),mode,str(fs*factor),str(raw),str(wet)],capture_output=True,text=True,check=True,timeout=30)
            y=np.fromfile(wet,dtype='<f4').reshape(-1,2)
            if factor>1:y=resample_poly(y.astype(np.float64),1,factor,axis=0).astype(np.float32)
            if factor>1:mode='oversampled_margin'
            if y.shape!=x.shape or not np.all(np.isfinite(y)):raise ValueError('Render length/finite validation failed')
            wavfile.write(out/(mode+'.wav'),fs,y)
            result['renders'][mode]={**metrics(y.astype(float),fs),'render_stdout':run.stdout.strip(),'oversampling_factor':factor}
    # For preference listening only, apply common attenuation after RMS matching to avoid clipping.
    base=read_audio(out/'baseline.wav')[1];cand=read_audio(out/'oversampled_margin.wav')[1]
    base_rms=np.sqrt(np.mean(base**2)); cand_rms=np.sqrt(np.mean(cand**2)); cand=cand*(base_rms/max(cand_rms,1e-15));factor=min(1,.95/max(np.max(np.abs(base)),np.max(np.abs(cand)),1e-15));
    wavfile.write(out/'matched_baseline.wav',fs,(base*factor).astype(np.float32));wavfile.write(out/'matched_oversampled.wav',fs,(cand*factor).astype(np.float32))
    result['listening_match']={'candidate_rms_adjust_db':db(base_rms/max(cand_rms,1e-15)),'common_attenuation_db':db(factor),'note':'Baseline versus 4x margin candidate. RMS-matched listening files, not LUFS-matched; raw measurements above unaffected.'}
    (out/'metrics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('out');p.add_argument('--renderer',required=True);p.add_argument('--seconds',type=int,default=12);a=p.parse_args();print(json.dumps(render(a.source,a.out,a.renderer,a.seconds),indent=2))
