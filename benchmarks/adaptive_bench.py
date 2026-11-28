"""Independent built-in fixtures, private audio held out. No commercial loading."""
import argparse,json,hashlib,math
from pathlib import Path
import numpy as np
import soundfile as sf
import pedalboard as pb
from scipy.signal import resample_poly
from skell_vst_decompiler.adaptive_behavior import envelope_features,fit_envelopes,bandlimited_tone,isolated_echoes
from skell_vst_decompiler.envelope_research import detector_frequency_models

def main():
    parser=argparse.ArgumentParser();parser.add_argument('sources',nargs='+',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    sources=[]
    for path in args.sources:
        x,fs=sf.read(path,always_2d=True);x=x[:12*fs];x=np.repeat(x,2,axis=1) if x.shape[1]==1 else x
        if x.shape[1]!=2:raise ValueError('unsupported channels')
        sources.append((hashlib.sha256(path.read_bytes()).hexdigest(),x,fs))
    count=0
    def render(name,kw,x,fs):
        nonlocal count
        y=getattr(pb,name)(**kw).process(np.ascontiguousarray(x.T,dtype=np.float32),fs,buffer_size=128,reset=True).T;count+=1
        if y.shape!=x.shape or not np.isfinite(y).all():raise ValueError('invalid fixture output')
        return y.astype(float)
    rms=lambda v:float(np.sqrt(np.mean(v*v)))
    rng=np.random.default_rng(713);out={'scope':'Independent Pedalboard 0.9.23 fixtures; no commercial target execution','envelopes':[],'detectors':[],'delay':[],'chorus':[],'isolated_color':[],'source_sha256':[s[0] for s in sources]}
    for fs in (44100,48000,96000):
        train=[];hold=[];kw={'threshold_db':-24,'ratio':4,'attack_ms':5,'release_ms':150}
        for j in range(4):
            t=np.arange(4*fs)/fs;env=np.repeat(rng.choice([.01,.035,.1,.2,.4,.7],16),fs//4);env=np.pad(env,(0,len(t)-len(env)),mode='edge');v=env*np.sin(2*np.pi*(200+200*j)*t);x=np.column_stack((v,v*.8));train.append(envelope_features(x,render('Compressor',kw,x,fs),fs))
        for _,x,sr in sources:
            d=math.gcd(fs,sr);v=resample_poly(x,fs//d,sr//d,axis=0);hold.append(envelope_features(v,render('Compressor',kw,v,fs),fs))
        models=fit_envelopes(train,hold);out['envelopes'].append({'rate':fs,'models':models});print('recovery',fs,[(r['model'],r['holdout_rmse_db']) for r in models],flush=True)
        for name,k in [('Compressor',{'threshold_db':-40,'ratio':4,'attack_ms':1,'release_ms':200}),('Limiter',{'threshold_db':-18,'release_ms':100})]:
            p=[];r=[];f=[];g=[];m=[]
            for hz in (80,200,1000,4000):
                for phase in (0.,1.3,2.7):
                    tone=bandlimited_tone(fs,hz,phase,2);tone/=max(abs(tone))
                    for amp in (.2,.4,.8):
                        x=np.column_stack((amp*tone,amp*tone));y=render(name,k,x,fs)[-fs:];x=x[-fs:];p.append(float(np.max(abs(x))));r.append(rms(x));f.append(hz);g.append(20*np.log10(max(rms(y),1e-15)/rms(x)));m.append(hz!=4000 and phase!=1.3)
            models=detector_frequency_models(p,r,f,g,np.array(m));out['detectors'].append({'rate':fs,'processor':name,'models':models});print('detector',fs,name,[(v['model'],round(v['heldout_rmse_db'],4)) for v in models],flush=True)
        # Exact source impulses with a long quiet suffix, feedback changes and wet-only path.
        for feedback in (.2,.6,.8):
            for ch in (0,1):
                x=np.zeros((6*fs,2));x[0,ch]=.5;y=render('Delay',{'delay_seconds':.12,'feedback':feedback,'mix':1.},x,fs)
                echoes=isolated_echoes(y[:,ch],fs);cross=float(np.max(abs(y[:,1-ch])))
                out['delay'].append({'rate':fs,'feedback':feedback,'input_channel':ch,'first_echoes':echoes[:6],'cross_peak':cross,'echo_count':len(echoes)})
        # Sparse impulses in one long render preserve modulation phase across input events.
        n=4*fs;x=np.zeros((n,2));starts=np.arange(0,n-fs//10,fs//10);x[starts,0]=.5
        y=render('Chorus',{'rate_hz':1.,'depth':.6,'centre_delay_ms':15.,'feedback':0.,'mix':1.},x,fs)
        points=[]
        for start in starts:
            segment=y[start+1:start+fs//20,0];j=int(np.argmax(abs(segment)))+1;points.append([float(start/fs),1000*j/fs,float(segment[j-1])])
        t,d,_=np.array(points).T;A=np.column_stack((np.ones(len(t)),np.sin(2*np.pi*t),np.cos(2*np.pi*t)));mask=t<2
        c=np.linalg.lstsq(A[mask],d[mask],rcond=None)[0];e=A[~mask]@c-d[~mask];out['chorus'].append({'rate':fs,'points':points,'holdout_delay_rmse_ms':rms(e),'delay_min_ms':float(min(d)),'delay_max_ms':float(max(d))})
        # Identical suffix under different histories, independent processors only.
        t=np.arange(2*fs)/fs;carrier=np.sin(2*np.pi*1000*t);base=.05*carrier;changed=base.copy();changed[:fs]=.9*carrier[:fs]
        for name,k in [('Clipping',{'threshold_db':-12}),('Distortion',{'drive_db':12}),('Limiter',{'threshold_db':-12,'release_ms':200})]:
            a=np.column_stack((base,base));b=np.column_stack((changed,changed));v=render(name,k,a,fs);w=render(name,k,b,fs)
            out['isolated_color'].append({'rate':fs,'processor':name,'identical_suffix_rms_difference':rms(v[fs:]-w[fs:]),'first_100ms_rms_difference':rms(v[fs:fs+fs//10]-w[fs:fs+fs//10])})
    out['render_count']=count;args.output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print('renders',count)
if __name__=='__main__':main()
