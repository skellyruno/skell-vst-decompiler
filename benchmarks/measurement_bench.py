import json, tempfile, hashlib, time
from pathlib import Path
import numpy as np
import scipy
import pedalboard as pb
from skell_vst_decompiler.measurement_lab import sweep,harmonic_windows,coherence_gate,model_screen,sample_surface,cached,parallel_measure


def main():
    rng=np.random.default_rng(271);report={'sweeps':[],'coherence':[],'models':[],'sampling':[],'cache':[]};renders=0
    def render(name,kw,x,fs):
        nonlocal renders
        y=getattr(pb,name)(**kw).process(np.ascontiguousarray(x[None,:],dtype=np.float32),fs,buffer_size=128,reset=True)[0];renders+=1
        if y.shape!=x.shape or not np.isfinite(y).all():raise ValueError('invalid render')
        return y.astype(float)
    for fs in (44100,48000,96000):
        x,inv,L=sweep(fs);a=np.pad(x,(0,fs//2))
        for name,kw in [('Gain',{'gain_db':-3}),('PeakFilter',{'cutoff_frequency_hz':1200,'gain_db':6,'q':1.2}),('Distortion',{'drive_db':18}),('Clipping',{'threshold_db':-12})]:
            y=render(name,kw,a,fs);report['sweeps'].append(dict(rate=fs,processor=name,orders=harmonic_windows(x,y,inv,L,fs)))
        a=rng.uniform(-.4,.4,fs);b=rng.uniform(-.6,.6,fs)
        for name,kw in [('Gain',{'gain_db':-3}),('Distortion',{'drive_db':12}),('Compressor',{'threshold_db':-24,'ratio':4,'attack_ms':5,'release_ms':100})]:
            y=render(name,kw,a,fs);z=render(name,kw,b,fs)
            report['models'].append(dict(rate=fs,processor=name,models=model_screen(a,y,b,z)))
        for noise in (0,.005,.05,.2):report['coherence'].append(dict(rate=fs,noise_rms=noise,**coherence_gate(a,.5*a+rng.normal(0,noise,len(a)),fs)))
    fs=48000;t=np.arange(fs//2)/fs;env=np.repeat([.03,.4,.07,.6],len(t)//4);x=env*np.sin(2*np.pi*220*t)
    grid=np.array([(a,b) for a in np.linspace(-1,1,11) for b in np.linspace(-1,1,11)]);hold=np.array([(a,b) for a in np.linspace(-.9,.9,6) for b in np.linspace(-.9,.9,6)])
    rms=lambda a:float(np.sqrt(np.mean(a*a)))
    for name in ('Compressor','PeakFilter','Delay'):
        def observe(q):
            a,b=(q+1)/2
            kw={'threshold_db':-40+30*a,'ratio':1+9*b} if name=='Compressor' else {'cutoff_frequency_hz':200+3800*a,'gain_db':-9+18*b,'q':1.2} if name=='PeakFilter' else {'delay_seconds':.03+.15*a,'feedback':.1+.7*b,'mix':.5}
            return 20*np.log10(max(rms(render(name,kw,x,fs)),1e-15)/rms(x))
        truth=np.array([observe(q) for q in hold]);row={'processor':name,'holdout_count':len(hold),'models':[]}
        for budget in (15,25,49):
            for adaptive in (False,True):
                ids,y=sample_surface(grid,observe,hold,budget=budget,adaptive=adaptive);row['models'].append(dict(budget=budget,adaptive=adaptive,holdout_rmse_db=rms(y-truth),indices=ids))
        report['sampling'].append(row)
    # Repeat only original numerical jobs; no parallel VST3 loading.
    xs=[rng.normal(0,.1,48000) for _ in range(24)];impl=hashlib.sha256(Path(__file__).read_bytes()+Path(__file__).resolve().parents[1].joinpath('skell_vst_decompiler/measurement_lab.py').read_bytes()).hexdigest()
    def worker(i):return coherence_gate(xs[i],xs[i]*.5,48000)
    t=time.perf_counter();a=parallel_measure(list(range(24)),worker,1);serial=time.perf_counter()-t
    t=time.perf_counter();b=parallel_measure(list(range(24)),worker,4);parallel=time.perf_counter()-t
    assert a==b
    with tempfile.TemporaryDirectory() as d:
        def run(i):return cached(d,dict(source_sha256=hashlib.sha256(xs[i].tobytes()).hexdigest(),implementation_sha256=impl,settings={'rate':48000,'gain':.5},versions={'numpy':np.__version__,'scipy':scipy.__version__}),lambda:worker(i))
        t=time.perf_counter();cold=parallel_measure(list(range(24)),run,4);cold_time=time.perf_counter()-t
        t=time.perf_counter();warm=parallel_measure(list(range(24)),run,4);warm_time=time.perf_counter()-t
        assert all(not hit for _,hit in cold) and all(hit for _,hit in warm) and [v for v,_ in cold]==[v for v,_ in warm]==a
    report.update(renders=renders,cache=dict(jobs=24,serial_seconds=serial,parallel_seconds=parallel,cold_seconds=cold_time,warm_seconds=warm_time,warm_hits=24))
    Path('measurement_results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('renders',renders);print('sweeps',[(r['rate'],r['processor'],[round(v['relative_window_db'],2) for v in r['orders']]) for r in report['sweeps']]);print('models',[(r['rate'],r['processor'],[round(v['holdout_rms'],6) for v in r['models']]) for r in report['models']]);print('sampling',[(r['processor'],[(v['budget'],v['adaptive'],round(v['holdout_rmse_db'],4)) for v in r['models']]) for r in report['sampling']]);print('coherence',[(r['rate'],r['noise_rms'],round(r['pass_fraction'],4)) for r in report['coherence']]);print('cache',report['cache'])
if __name__=='__main__':main()
