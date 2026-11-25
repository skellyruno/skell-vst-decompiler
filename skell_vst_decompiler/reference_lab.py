"""Offline probe generation and aligned render measurement; no plugin loading.

All stimulus audio is original synthetic material. Settings and render identity
are supplied by the operator, not authenticated by the analyzer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.optimize import least_squares
from scipy.signal import chirp
from .pitch_reference import estimate

RATES=(44100,48000,96000)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def probes(fs):
    if fs not in RATES:raise ValueError('Unsupported sample rate')
    def tone(seconds,hz,db):
        return 10**(db/20)*np.sin(2*np.pi*hz*np.arange(round(seconds*fs))/fs)
    def stereo(x):return np.column_stack((x,x))
    def levels(values):
        a=[];windows=[];pos=0
        for db in values:
            x=tone(2.,1000,db);a.append(x)
            windows.append({'start':pos+round(1.5*fs),'stop':pos+len(x),'level_dbfs_peak':db});pos+=len(x)
        return stereo(np.concatenate(a)),windows
    impulse=np.zeros((2*fs,2));impulse[fs//4,0]=.25;impulse[5*fs//4,1]=.25
    yield 'impulse','linear',impulse,[]
    t=np.arange(4*fs)/fs
    sweep=.1*chirp(t,30,4,18000,method='logarithmic');fade=np.minimum(1,np.minimum(t*50,(4-t)*50));sweep*=fade
    yield 'sweep','linear',stereo(sweep),[]
    for name,values in [('levels_train',(-42,-30,-24,-18,-12,-6)),('levels_holdout',(-36,-27,-21,-15,-9,-3))]:
        x,w=levels(values);yield name,'dynamics',x,w
    x=np.concatenate([tone(d,1000,l) for d,l in [(1,-36),(.25,-6),(2,-36),(2,-6),(3,-36)]])
    yield 'history_steps','dynamics',stereo(x),[]
    t=np.arange(2*fs)/fs;x=.16*np.sin(2*np.pi*1700*t)+.16*np.sin(2*np.pi*2300*t)
    yield 'two_tone','nonlinear',stereo(x),[]
    x=tone(1,200,-18);zero=np.zeros_like(x)
    yield 'stereo_detector','dynamics',np.concatenate([np.column_stack((x,x)),np.column_stack((x,-x)),np.column_stack((x,zero)),np.column_stack((x,np.roll(x,round(fs/800))))]),[]
    t=np.arange(4*fs)/fs
    for name,f in [('pitch_steps',np.repeat([196.,220.,246.94,220.],fs)),('vibrato',220*2**((35*np.sin(2*np.pi*5*t))/1200)),('pitch_glide',180*2**(t/8))]:
        phase=2*np.pi*np.cumsum(f)/fs;x=sum(.28/k*np.sin(k*phase) for k in range(1,5))
        yield name,'pitch',stereo(x),[]
    # Synthetic harmonic vowel-like stimulus, not a human vocal or a phoneme model.
    phase=2*np.pi*180*t;weights=[np.exp(-.5*((180*k-700)/130)**2)+.5*np.exp(-.5*((180*k-1200)/200)**2) for k in range(1,24)]
    x=sum(w*np.sin(k*phase) for k,w in enumerate(weights,1));x*=.35/max(np.max(np.abs(x)),1e-12)
    yield 'vowel_like','pitch',stereo(x),[]


def generate(root,fs=48000):
    root=Path(root);root.mkdir(parents=True,exist_ok=False);cases=[]
    for key,family,a,windows in probes(fs):
        path=root/(key+'.wav');sf.write(path,a,fs,subtype='FLOAT')
        cases.append({'id':key,'family':family,'file':path.name,'sha256':digest(path),'frames':len(a),'channels':2,'windows':windows})
    m={'schema':1,'sample_rate':fs,'cases':cases,'note':'Original synthetic stimuli; render each file from reset state, no normalization, no resampling.'}
    (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    return m


def measure(root,case_id,wet,metadata):
    root=Path(root);m=json.loads((root/'manifest.json').read_text());fs=m['sample_rate']
    if m.get('schema')!=1 or fs not in RATES:raise ValueError('Unknown probe manifest')
    cases=[c for c in m['cases'] if c['id']==case_id]
    if len(cases)!=1:raise ValueError('Unknown or duplicate case')
    c=cases[0];name=c['file']
    if name!=case_id+'.wav' or Path(name).name!=name:raise ValueError('Invalid source filename')
    dry=root/name
    if digest(dry)!=c['sha256'] or metadata.get('source_sha256')!=c['sha256']:raise ValueError('Source identity mismatch')
    for k in ('plugin','version','settings'):
        if not isinstance(metadata.get(k),str) or not metadata[k].strip():raise ValueError('Missing render '+k)
    lag=metadata.get('offset_samples')
    if type(lag) is not int or not 0<=lag<=fs*2:raise ValueError('Explicit nonnegative alignment offset required')
    wet=Path(wet);wet_hash=digest(wet)
    if wet_hash!=metadata.get("render_sha256"):raise ValueError("Render identity mismatch")
    a,sr=sf.read(dry,always_2d=True);info=sf.info(wet)
    if sr!=fs or info.samplerate!=fs or a.shape!=(c['frames'],2) or info.channels!=2 or not len(a)+lag<=info.frames<=len(a)+lag+fs*10:raise ValueError('Rate/channel/length mismatch')
    b,_=sf.read(wet,start=lag,frames=len(a),always_2d=True)
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or np.max(np.abs(b))>64:raise ValueError('Invalid samples')
    def rms(x):return float(np.sqrt(np.mean(x*x)))
    def db(x):return float(20*np.log10(max(x,1e-15)))
    n=round(fs*.01);curve=[]
    for i in range(0,len(a)-n+1,n):
        x,y=a[i:i+n],b[i:i+n];v=rms(x)
        if v>1e-6:curve.append({'time_ms':1000*i/fs,'gain_db':db(rms(y)/v)})
    windows=[]
    for w in c['windows']:
        lo,hi=w['start'],w['stop']
        if not 0<=lo<hi<=len(a):raise ValueError('Invalid measurement window')
        x,y=a[lo:hi],b[lo:hi];v=rms(x)
        windows.append({'input_rms_db':db(v),'gain_db':db(rms(y)/max(v,1e-15))})
    report={'case_id':case_id,'family':c['family'],'sample_rate':fs,'source_sha256':c['sha256'],'render_sha256':wet_hash,'metadata':metadata,'frames':len(a),'unused_tail_frames':info.frames-lag-len(a),'input_rms_db':db(rms(a)),'output_rms_db':db(rms(b)),'sample_peak_dbfs':db(float(np.max(np.abs(b)))),'relative_waveform_error_db':db(rms(b-a)/max(rms(a),1e-15)),'windows':windows,'gain_curve':curve,'note':'Operator-declared alignment/settings, not inferred. RMS gain includes distortion.'}
    if case_id=='two_tone':
        # Integer-cycle final second, selected components only.
        z=b[-fs:];s=np.fft.rfft(z,axis=0)/fs;fund=np.sum(np.abs(s[[1700,2300]])**2)
        report['selected_imd_db']=db(np.sqrt(np.sum(np.abs(s[[600,4000,1100,2900]])**2)/fund)) if fund>1e-20 else None
    if case_id=='impulse':
        matrix=[]
        for source,origin in [(0,fs//4),(1,5*fs//4)]:
            segment=b[origin:origin+fs//2]/.25
            spectrum=np.fft.rfft(segment,axis=0)
            matrix.append({'source_channel':source,'peak_delay_samples':[int(np.argmax(np.abs(segment[:,i]))) if np.max(np.abs(segment[:,i]))>1e-9 else None for i in range(2)],'response_db':{str(f):[db(float(v)) for v in np.abs(spectrum[f//2])] for f in (100,1000,5000,10000)}})
        report['impulse_response']=matrix
        report['impulse_note']='Half-second impulse windows; only meaningful for linear time-invariant settings.'
    if c['family']=='pitch':
        frame=round(.065*fs);hop=round(.01*fs);trace=[]
        for i in range(0,len(a)-frame+1,hop):
            dry_f,dry_q=estimate(a[i:i+frame,0],fs,backend='fft')
            wet_f,wet_q=estimate(b[i:i+frame,0],fs,backend='fft')
            trace.append({'frame_end_ms':1000*(i+frame)/fs,'dry_hz':dry_f,'wet_hz':wet_f,'dry_periodicity':dry_q,'wet_periodicity':wet_q,'shift_cents':float(1200*np.log2(wet_f/dry_f)) if dry_f and wet_f else None})
        report['pitch_trace']=trace
        report['pitch_note']='65 ms analysis windows, labelled by frame end; estimator error and window response are not plugin latency.'
    if digest(dry)!=c['sha256'] or digest(wet)!=wet_hash:raise ValueError('Input changed during analysis')
    return report


def fit_curve(train,holdout):
    """Original hard-knee descriptive model, scored on distinct levels."""
    if train['case_id']!='levels_train' or holdout['case_id']!='levels_holdout' or train['sample_rate']!=holdout['sample_rate']:raise ValueError('Wrong fitting/holdout cases')
    if any(train['metadata'][k]!=holdout['metadata'][k] for k in ('plugin','version','settings','offset_samples')):raise ValueError('Render settings mismatch')
    def arrays(r):
        x=np.array([w['input_rms_db'] for w in r['windows']]);y=np.array([w['gain_db'] for w in r['windows']]);return x,y
    x,y=arrays(train);xh,yh=arrays(holdout)
    if min(len(x),len(xh))<4 or not np.all(np.isfinite(np.r_[x,y,xh,yh])):raise ValueError('Insufficient levels')
    def predict(p,z):return p[2]-p[1]*np.maximum(0,z-p[0])
    fit=least_squares(lambda p:predict(p,x)-y,[-24.,.5,0.],bounds=([-60.,0.,-30.],[0.,.99,30.]))
    if not fit.success:raise RuntimeError('Fit failed')
    p=fit.x
    identifiable=bool(np.sum(x<p[0])>=2 and np.sum(x>p[0])>=2 and p[1]>.01)
    return {'threshold_bracketed':identifiable,'threshold_rms_db':float(p[0]),'ratio':float(1/(1-p[1])),'makeup_db':float(p[2]),'train_rmse_db':float(np.sqrt(np.mean((predict(p,x)-y)**2))),'heldout_rmse_db':float(np.sqrt(np.mean((predict(p,xh)-yh)**2))),'heldout_constant_gain_rmse_db':float(np.sqrt(np.mean((np.mean(y)-yh)**2))),'note':'Descriptive hard knee; not proof of an internal detector or compressor law.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    g=sub.add_parser('generate');g.add_argument('folder');g.add_argument('--rate',type=int,default=48000)
    a=sub.add_parser('measure');a.add_argument('folder');a.add_argument('case');a.add_argument('wet');a.add_argument('metadata')
    f=sub.add_parser('fit');f.add_argument('train');f.add_argument('holdout')
    x=p.parse_args()
    if x.action=='generate':result=generate(x.folder,x.rate)
    elif x.action=='measure':result=measure(x.folder,x.case,x.wet,json.loads(Path(x.metadata).read_text()))
    else:result=fit_curve(json.loads(Path(x.train).read_text()),json.loads(Path(x.holdout).read_text()))
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
