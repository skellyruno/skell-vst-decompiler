"""Independent fixture benchmark; private recordings never written to reports."""
import argparse,json,io,zipfile,hashlib
from pathlib import Path
import numpy as np
import pedalboard as pb
import soundfile as sf
from skell_vst_decompiler.interaction_analysis import factorial,history

CONFIGS=[('Compressor',{'threshold_db':(-30.,-12.),'ratio':(2.,8.)},{'attack_ms':5.,'release_ms':100.}),('Compressor',{'attack_ms':(1.,50.),'release_ms':(30.,500.)},{'threshold_db':-24.,'ratio':8.}),('NoiseGate',{'threshold_db':(-45.,-20.),'ratio':(2.,10.)},{'attack_ms':2.,'release_ms':100.}),('Delay',{'feedback':(.15,.7),'mix':(.2,.7)},{'delay_seconds':.12}),('Reverb',{'room_size':(.2,.8),'damping':(.1,.8)},{'wet_level':.5,'dry_level':.5,'width':1.}),('Chorus',{'rate_hz':(.7,3.),'depth':(.15,.8)},{'mix':.5,'centre_delay_ms':12.,'feedback':.15}),('Limiter',{'threshold_db':(-18.,-3.),'release_ms':(20.,250.)},{}),('PeakFilter',{'cutoff_frequency_hz':(300.,2200.),'gain_db':(-6.,9.)},{'q':1.2}),('HighShelfFilter',{'cutoff_frequency_hz':(1000.,5000.),'gain_db':(-6.,9.)},{'q':.7})]

def main():
    p=argparse.ArgumentParser();p.add_argument('private_zip',type=Path);p.add_argument('output',type=Path);a=p.parse_args();fs=48000;rng=np.random.default_rng(904);t=np.arange(fs)/fs
    env=np.repeat([.03,.5,.08,.6],fs//4);x=env*(np.sin(2*np.pi*220*t)+.25*np.sin(2*np.pi*2600*t));synthetic=np.column_stack((x,.7*x+ .03*np.sin(2*np.pi*1100*t))).astype(np.float32)
    noise=(rng.uniform(-1,1,(fs,2))*env[:,None]).astype(np.float32)
    sources={'tone_steps':synthetic,'independent_noise':noise}; hashes={}
    with zipfile.ZipFile(a.private_zip) as z:
        for name in ('A','B'):
            raw=z.read(f'{name}_recorded_vocal/original.wav');x,sr=sf.read(io.BytesIO(raw),dtype='float32',always_2d=True)
            if sr!=fs or x.shape[1]!=2 or len(x)<fs:raise ValueError('private input format')
            sources['recorded_'+name]=x[:fs];hashes[name]=hashlib.sha256(raw).hexdigest()
    results=[]; state=[]; renders=0
    def render(name,settings,x):
        nonlocal renders
        fx=getattr(pb,name)(**settings);y=fx.process(np.ascontiguousarray(x.T),fs,buffer_size=128,reset=True).T;renders+=1
        if y.shape!=x.shape or not np.isfinite(y).all():raise ValueError(f'invalid output for {name}')
        return y
    for name,axes,fixed in CONFIGS:
        keys=list(axes)
        for label,sig in sources.items():
            sig=np.pad(sig,((0,fs),(0,0)))
            cells={}
            for cell in ('00','10','01','11'):
                settings={**fixed,**{k:axes[k][int(b)] for k,b in zip(keys,cell)}}
                cells[cell]=[render(name,settings,sig) for _ in range(2)]
            results.append(dict(processor=name,controls=keys,source=label,**factorial(cells)))
        for label in ('tone_steps','recorded_A','recorded_B'):
            x=sources[label];prefix=fs//2;suffix=np.concatenate([x[prefix:],np.zeros((fs,2),np.float32)])
            dry_a=np.concatenate([np.zeros_like(x[:prefix]),suffix]);dry_b=np.concatenate([x[:prefix],suffix]);settings={**fixed,**{k:v[1] for k,v in axes.items()}}
            cells={k:[render(name,settings,z) for _ in range(2)] for k,z in (('a',dry_a),('b',dry_b))}
            r=history(dry_a,dry_b,cells,fs,prefix);r.pop('windows');state.append(dict(processor=name,controls=keys,source=label,**r))
    report=dict(scope='Independent Pedalboard built-in processors only, no commercial target render or model claim',version=pb.__version__,rate=fs,block=128,configs=CONFIGS,private_source_sha256=hashes,actual_renders=renders,factorial=results,history=state)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    from collections import Counter
    print('renders',renders,'factorial',Counter(x['status'] for x in results),'history',Counter(x['status'] for x in state))
    for name,axes,_ in CONFIGS:
        rows=[r for r in results if r['processor']==name and r['controls']==list(axes)]; h=[r for r in state if r['processor']==name and r['controls']==list(axes)]
        print(name,list(axes), 'additive residual %', [round(100*r['additive_relative_error'],3) if r['additive_relative_error'] is not None else None for r in rows], 'history ms',[(r['last_detected_end_ms'],r['right_censored'],r['status']) for r in h], 'max repeat',max(r['repeat_rms'] for r in rows))
if __name__=='__main__':main()
