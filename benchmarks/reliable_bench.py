"""Independent fixtures, no commercial loading. Run in scratch directory."""
import json,time,tempfile,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import pedalboard as pb
from skell_vst_decompiler.reliable_measurement import harmonic_levels,repeated_spectrum,static_descriptions,SingleFlightCache
from skell_vst_decompiler.measurement_lab import sample_surface


def main():
    rng=np.random.default_rng(531);report=dict(harmonics=[],repeats=[],models=[],sampling=[]);renders=0
    def render(name,kw,x,fs):
        nonlocal renders
        y=getattr(pb,name)(**kw).process(np.ascontiguousarray(x[None,:],dtype=np.float32),fs,buffer_size=128,reset=True)[0];renders+=1
        if y.shape!=x.shape or not np.isfinite(y).all():raise ValueError('invalid render')
        return y.astype(float)
    for fs in (44100,48000,96000):
        for name,kw in [('Gain',{'gain_db':-3}),('PeakFilter',{'cutoff_frequency_hz':1000,'gain_db':6,'q':1.2}),('Distortion',{'drive_db':18}),('Clipping',{'threshold_db':-12})]:
            for hz in (200,1000,3000):
                for amp in (.05,.3,.7):
                    x=amp*np.sin(2*np.pi*hz*np.arange(2*fs)/fs);y=render(name,kw,x,fs)
                    report['harmonics'].append(dict(rate=fs,processor=name,hz=hz,peak=amp,**harmonic_levels(x[-fs:],y[-fs:],fs,hz)))
        # Three disjoint sequences. Validation uses independent random phase and level distribution.
        tr=np.r_[-.95,np.linspace(-.95,.95,fs-2),.95];rng.shuffle(tr)
        v=rng.uniform(-.9,.9,fs);t=np.arange(fs)/fs;z=.65*np.sin(2*np.pi*221*t)+.2*np.cos(2*np.pi*873*t)
        for name,kw in [('Gain',{'gain_db':-3}),('Distortion',{'drive_db':12}),('Clipping',{'threshold_db':-12}),('Compressor',{'threshold_db':-24,'ratio':4,'attack_ms':5,'release_ms':100})]:
            a,b,c=[render(name,kw,x,fs) for x in (tr,v,z)];report['models'].append(dict(rate=fs,processor=name,**static_descriptions(tr,a,v,b,z,c)))
        x=rng.normal(0,.08,fs*2)
        for name,kw in [('Gain',{'gain_db':-3}),('PeakFilter',{'cutoff_frequency_hz':1000,'gain_db':6}),('Compressor',{'threshold_db':-24,'ratio':4}),('Chorus',{'depth':.6,'rate_hz':.73})]:
            y=[render(name,kw,x,fs) for _ in range(3)];report['repeats'].append(dict(rate=fs,processor=name,**repeated_spectrum(x,y,fs)))
    # Same fixed physical holdout and budget; change parameter coordinate geometry only.
    fs=48000;hz=1000;t=np.arange(fs//2)/fs;x=.3*np.sin(2*np.pi*hz*t)
    grid=np.array([(a,b) for a in np.linspace(-1,1,11) for b in np.linspace(-1,1,11)]);hold=np.array([(a,b) for a in np.linspace(-.9,.9,6) for b in np.linspace(-.9,.9,6)])
    def transform(q):
        q=q.copy();q[:,0]=2*np.log((200+(q[:,0]+1)*1900)/200)/np.log(20)-1;return q
    def observe(q):
        y=render('PeakFilter',{'cutoff_frequency_hz':200+(q[0]+1)*1900,'gain_db':9*q[1],'q':1.2},x,fs);return float(20*np.log10(np.linalg.norm(y[fs//4:])/np.linalg.norm(x[fs//4:])))
    truth=np.array([observe(q) for q in hold]);values={}
    for budget in (15,25,49):
        for log in (False,True):
            a,b=(transform(grid),transform(hold)) if log else (grid,hold)
            def get(q):
                i=int(np.argmin(np.linalg.norm(a-q,axis=1)));key=tuple(grid[i]);
                if key not in values:values[key]=observe(grid[i])
                return values[key]
            ids,pred=sample_surface(a,get,b,budget=budget,adaptive=False);report['sampling'].append(dict(budget=budget,log_coordinate=log,holdout_rmse_db=float(np.sqrt(np.mean((pred-truth)**2)))))
    # Duplicate jobs with an artificial expensive independent compute, not real render speed.
    with tempfile.TemporaryDirectory() as d:
        c=SingleFlightCache(d);k=dict(source_sha256='a'*64,implementation_sha256='b'*64,settings={'fixture':1},versions={'numpy':np.__version__});calls=[];guard=threading.Lock()
        def work():
            with guard:calls.append(1)
            time.sleep(.02);return {'v':1}
        start=time.perf_counter()
        with ThreadPoolExecutor(4) as pool:out=list(pool.map(lambda _:c.get(k,work),range(32)))
        report['cache']=dict(requests=32,computations=len(calls),hits=sum(h for _,h in out),elapsed_seconds=time.perf_counter()-start)
    report['renders']=renders;report['scope']='Independent Pedalboard built-in fixtures, synthetic input only; no commercial matching';Path('reliable_results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('renders',renders);print('harmonic 48k 1k .3',[(r['processor'],r['thd_selected'],r['other_ac_rms']) for r in report['harmonics'] if r['rate']==48000 and r['hz']==1000 and r['peak']==.3]);print('models',[(r['rate'],r['processor'],r['selected'],r['linear_final_test_rms'],r['final_test_rms']) for r in report['models']]);print('repeats',[(r['rate'],r['processor'],r['status'],r['worst_coherence_pass_fraction']) for r in report['repeats']]);print('sampling',report['sampling']);print('cache',report['cache'])
if __name__=='__main__':main()
