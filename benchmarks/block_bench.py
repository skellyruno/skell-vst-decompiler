"""Independent Pedalboard fixture chains, no commercial target."""
import argparse,json,math,time
from pathlib import Path
import numpy as np
import pedalboard as pb
import soundfile as sf
from scipy.signal import resample_poly,sosfilt,butter
from skell_vst_decompiler.block_identification import predict,fit_orders


def main():
    p=argparse.ArgumentParser();p.add_argument('sources',nargs='+');p.add_argument('--output',required=True);a=p.parse_args()
    rng=np.random.default_rng(335);count=0;results=[]
    def render(x,fs,kind):
        nonlocal count
        fx=[]
        if kind in ('pre','split'):fx.append(pb.LowpassFilter(cutoff_frequency_hz=3400))
        if kind=='compressor':fx.append(pb.Compressor(threshold_db=-24,ratio=4,attack_ms=5,release_ms=100))
        else:fx.append(pb.Distortion(drive_db=14))
        if kind in ('post','split','compressor'):fx.append(pb.LowpassFilter(cutoff_frequency_hz=6900))
        y=pb.Pedalboard(fx).process(x.astype(np.float32)[None,:],fs,buffer_size=128,reset=True)[0].astype(float);count+=1;return (x,y,fs)
    def signal(fs,k):
        n=fs//4;t=np.arange(n)/fs
        if k==0:return rng.uniform(-.7,.7,n)
        if k==1:return .6*np.sin(2*np.pi*517*t)+.25*np.sin(2*np.pi*6113*t)
        if k==2:return .35*np.sin(2*np.pi*223*t)+.18*np.sin(2*np.pi*8291*t)+.1*rng.uniform(-1,1,n)
        return sosfilt(butter(2,5000,fs=fs,output='sos'),rng.uniform(-.9,.9,n))
    for kind in ('pre','post','split','compressor'):
        train=[render(signal(48000,k),48000,kind) for k in (0,1)];valid=[render(signal(fs,k),fs,kind) for fs,k in ((44100,2),(96000,3))]
        t=time.perf_counter();fit=fit_orders(train,valid);fit['fit_seconds']=time.perf_counter()-t;print(kind,fit,flush=True)
        hold=[]
        if fit['selected']:
            winner=fit['selected'];baseline=min((dict(order=o['filter_order'],**r) for o in fit['orders'] for r in o['candidates'] if r['converged'] and r['model'] in ('static','pre','post')),key=lambda r:r['validation_relative_rms'])
            for fs in (44100,48000,96000,192000):
                for k,path in enumerate(a.sources):
                    x,sr=sf.read(path,always_2d=True);x=x[:2*sr,0];d=math.gcd(fs,sr);x=resample_poly(x,fs//d,sr//d);row=render(x,fs,kind);den=max(np.linalg.norm(row[1]),1e-12)
                    hold.append(dict(rate=fs,source=k,selected_relative_rms=float(np.linalg.norm(predict(x,fs,winner['model'],winner['parameters'],winner['order'])-row[1])/den),simpler_relative_rms=float(np.linalg.norm(predict(x,fs,baseline['model'],baseline['parameters'],baseline['order'])-row[1])/den)))
        results.append(dict(fixture=kind,fit=fit,holdout=hold));print(kind,'holdout',hold,flush=True)
    Path(a.output).write_text(json.dumps(dict(scope='independent fixed fixture chains; synthetic train/validation; reused recorded holdouts',renders=count,results=results),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
