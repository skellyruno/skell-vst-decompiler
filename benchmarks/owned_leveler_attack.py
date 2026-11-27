"""Independent leveler attack calibration; private audio and individual rows stay local."""
import argparse, ctypes as C, hashlib, json, pathlib, subprocess, tempfile
import numpy as np
import soundfile as sf
ROOT=pathlib.Path(__file__).resolve().parents[1]
def rms(x):return float(np.sqrt(np.mean(x*x)))
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'leveler.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_leveler_attack.cpp'),'-o',str(lib)],check=True)
        f=C.CDLL(str(lib)).leveler_attack;ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS');f.argtypes=[C.c_int,C.c_double,C.c_double,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int
        def render(k,fs,attack,wet,x):
            y=np.empty_like(x)
            if f(k,fs,attack,wet,x,y,len(x))!=1 or not np.isfinite(y).all():raise RuntimeError('Render failed')
            return y
        step=[];tones=[];vocals=[];calibrated=[];recovery=[];matched_vocals=[];seen=set();matched_attack={}
        for fs in (44100,48000,96000):
            for attack in (1,4,10,30):
                x=np.full((fs*2,2),.5);ys=[render(k,fs,attack,1,x) for k in (0,1)]
                target=(10**(-18/20)/.5)**.75;gr=-db(target)
                def onset(y):
                    reduction=-20*np.log10(np.maximum(y[:,0]/.5,1e-15));hits=np.flatnonzero(reduction>=.9*gr)
                    return float((hits[0]+1)*1000/fs) if len(hits) else None
                step.append({'fs':fs,'attack_ms':attack,'steady_gr_db':gr,'t90_gr_ms':[onset(y) for y in ys],'gr_after_4ms_db':[-db(y[round(.004*fs)-1,0]/.5) for y in ys]})
            # Match 90% steady-state reduction time, not the nominal knob label.
            probe=np.full((fs//2,2),.5);steady=-db((10**(-18/20)/.5)**.75)
            def onset_samples(k,attack):
                y=render(k,fs,attack,1,probe)
                hits=np.flatnonzero(-20*np.log10(np.maximum(y[:,0]/.5,1e-15))>=.9*steady)
                if not len(hits):raise RuntimeError('Attack did not settle')
                return int(hits[0]+1)
            target=onset_samples(0,4);lo,hi=4.,12.
            for _ in range(20):
                mid=(lo+hi)/2
                if onset_samples(1,mid)<target:lo=mid
                else:hi=mid
            tuned=hi;actual=onset_samples(1,tuned)
            if abs(actual-target)>1:raise RuntimeError('Matched attack calibration failed')
            matched_attack[fs]=tuned
            calibrated.append({'fs':fs,'baseline_attack_ms':4,'candidate_attack_ms':tuned,'baseline_t90_samples':target,'candidate_t90_samples':actual})
            for length_ms in (10,50,250,1000):
                n=round(fs*length_ms/1000);burst=np.full((n+2*fs,2),.025);burst[:n]=.5
                ys=[render(0,fs,4,1,burst),render(1,fs,4,1,burst),render(1,fs,tuned,1,burst)]
                gains=[-20*np.log10(np.maximum(y[n:,0]/.025,1e-15)) for y in ys]
                # First crossing of 10% of initial reduction, relative to each burst's own state.
                def release(g):
                    hits=np.flatnonzero(g<=.1*g[0]);return float(hits[0]*1000/fs) if len(hits) else None
                recovery.append({'fs':fs,'burst_ms':length_ms,'initial_gr_db':[float(g[0]) for g in gains],'release_to_10_percent_ms':[release(g) for g in gains]})
            for hz in (50,100,200,1000):
                t=np.arange(fs*2)/fs;x=np.ascontiguousarray(np.column_stack((.5*np.sin(2*np.pi*hz*t),.25*np.sin(2*np.pi*hz*t))))
                ys=[render(0,fs,4,1,x)[-fs:,0],render(1,fs,4,1,x)[-fs:,0],render(1,fs,tuned,1,x)[-fs:,0]]
                def distortion(y):
                    bins=np.abs(np.fft.rfft(y))**2;fund=bins[hz];return float(10*np.log10(max(np.sum(bins[2*hz::hz])/fund,1e-30)))
                tones.append({'fs':fs,'hz':hz,'thd_dbc':[distortion(y) for y in ys],'rms_gain_db':[db(rms(y)/rms(x[-fs:,0])) for y in ys]})
        for item in json.loads(a.manifest.read_text())['inputs']:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid input')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            x=np.ascontiguousarray(x);cases=[]
            for attack in (1,4,10):
                ys=[render(k,fs,attack,1,x) for k in (0,1)]
                matched=ys[1]*(rms(ys[0])/rms(ys[1]));active=np.max(np.abs(x),axis=1)>1e-5
                # Use the louder channel's linked gain estimate; exclude near-silent pairs.
                ii=np.argmax(np.abs(x),axis=1);idx=np.arange(len(x));g=[y[idx,ii][active]/x[idx,ii][active] for y in ys]
                cases.append({'attack_ms':attack,'raw_gain_db':[db(rms(y)/rms(x)) for y in ys],'peak_dbfs':[db(np.max(np.abs(y))) for y in ys],'over_scale_samples':[int(np.count_nonzero(np.abs(y)>1)) for y in ys],'median_gain_db':[float(np.median(20*np.log10(np.maximum(v,1e-15)))) for v in g],'matched_difference_db':db(rms(matched-ys[0])/rms(ys[0]))})
            if fs not in matched_attack:raise ValueError('Uncalibrated input sample rate')
            ys=[render(0,fs,4,1,x),render(1,fs,matched_attack[fs],1,x)]
            matched=ys[1]*(rms(ys[0])/rms(ys[1]))
            matched_vocals.append({'id':item['id'],'stage':item['stage'],'fs':fs,'peak_dbfs':[db(np.max(np.abs(y))) for y in ys],'raw_gain_db':[db(rms(y)/rms(x)) for y in ys],'matched_difference_db':db(rms(matched-ys[0])/rms(ys[0])),'over_scale_samples':[int(np.count_nonzero(np.abs(y)>1)) for y in ys]})
            vocals.append({'id':item['id'],'stage':item['stage'],'fs':fs,'frames':len(x),'cases':cases})
    a.output.write_text(json.dumps({'schema':1,'step_rows':step,'tone_rows':tones,'vocal_rows':vocals,'matched_attack_calibration':calibrated,'matched_vocal_rows':matched_vocals,'release_rows':recovery,'limits':'Independent source-known engines, not vendor matching. Step t90 is 90 percent of steady gain reduction in dB; coherent steady-tone THD includes in-band harmonic bins, not alias isolation. Tone and release arrays: original 4ms, candidate 4ms, candidate matched t90. Sample peaks only. No listening or host validation.'},indent=2)+'\n')
if __name__=='__main__':main()
