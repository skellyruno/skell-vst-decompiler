"""Offline independent 4x color filter split: same span, matched fundamental/RMS.
No vendor code or runtime DSP claim. Keep private manifests and results local.
"""
import argparse,hashlib,json,pathlib
import numpy as np
import soundfile as sf
from scipy.signal import firwin,upfirdn,lfilter
VARIANTS=((.45,.45),(.475,.45),(.45,.475),(.475,.475))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def render(x,fs,up,down):
    h1=firwin(161,up/2,window='blackman');h2=firwin(161,down/2,window='blackman')
    v=upfirdn(4*h1,x,up=4,axis=0);v=np.clip(v,-8,8);d=10**(.6);v=np.tanh(d*(v+.12*v*v))/np.tanh(d)
    p=np.exp(-2*np.pi*5/(4*fs));v=lfilter([1,-1],[1,-p],v,axis=0)
    y=upfirdn(h2,v,down=4,axis=0)[40:40+len(x)]
    if y.shape!=x.shape or not np.isfinite(y).all():raise RuntimeError('Invalid render')
    return y

def spectrum(x,fs,hz):
    n=len(x);z=np.abs(np.fft.rfft(x))**2;z[1:len(z)-(n%2==0)]*=2;k=round(hz*n/fs);fund=z[k];harm=np.arange(k,len(z),k);hd=z[harm[1:]].sum();z[0]=0;z[harm]=0
    return np.sqrt(2*fund)/n,np.sqrt(z.sum()/fund),np.sqrt(hd/fund)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();tones=[];vocals=[];seen=set()
    for fs in (44100,48000,96000):
        t=np.arange(fs+fs//4+128)/fs
        for hz in (3004,11004,17004,20004):
            for amp in (.1,.5,.9):
                x=np.column_stack((amp*np.sin(2*np.pi*hz*t),amp*np.cos(2*np.pi*hz*t)));values=[]
                for u,d in VARIANTS:
                    y=render(x,fs,u,d)[fs:fs+fs//4,0];fund,res,thd=spectrum(y,fs,hz)
                    values.append({'fundamental_dbfs':db(fund),'residual_dbc':db(res),'thd_dbc':db(thd),'absolute_residual_rms_dbfs':db(fund*res/np.sqrt(2))})
                tones.append({'fs':fs,'hz':hz,'amplitude':amp,'metrics':values})
    for item in json.loads(a.manifest.read_text())['inputs']:
        src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
        if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
        seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
        if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid input')
        if x.shape[1]==1:x=np.repeat(x,2,axis=1)
        ys=[render(x,fs,u,d) for u,d in VARIANTS];values=[]
        def band(y):
            z=np.abs(np.fft.rfft(y,axis=0))**2;f=np.fft.rfftfreq(len(y),1/fs);return float(z[(f>=8000)&(f<16000)].sum()/max(z.sum(),1e-30))
        for y in ys:
            m=y*rms(ys[0])/rms(y);values.append({'raw_peak_dbfs':db(np.max(np.abs(y))),'matched_peak_dbfs':db(np.max(np.abs(m))),'gain_db':db(rms(y)/rms(x)),'relative_high_band_db':10*np.log10(max(band(m),1e-30)),'over_scale_samples':int(np.count_nonzero(np.abs(y)>1))})
        vocals.append({'id':item['id'],'stage':item['stage'],'metrics':values})
    a.output.write_text(json.dumps({'schema':1,'variants':VARIANTS,'tones':tones,'vocals':vocals,'limits':'Offline independently implemented FIR color chain, 40 sample total alignment; not exact native engine parity. Nonharmonic residual excludes coincident harmonic bins; no true peak or listening claims.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
