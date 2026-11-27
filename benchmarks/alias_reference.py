"""Offline original saturation audit against converging high-rate references."""
import argparse,hashlib,json,pathlib
import numpy as np
import soundfile as sf
from scipy.signal import firwin,upfirdn,lfilter

def rms(x):return float(np.sqrt(np.mean(x*x)))
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def shape(x,fs,factor):
    x=np.clip(x,-8,8);d=10**.6
    v=np.tanh(d*(x+.12*x*x))/np.tanh(d)
    p=np.exp(-2*np.pi*5/(factor*fs))
    return lfilter([1,-1],[1,-p],v,axis=0)
def render(x,fs,factor,span,up,down,beta=None):
    n=factor*span+1
    h=firwin(n,up/factor,fs=1.,window='blackman' if beta is None else ('kaiser',beta))
    q=firwin(n,down/factor,fs=1.,window='blackman')
    v=upfirdn(factor*h,x,up=factor,axis=0)
    y=upfirdn(q,shape(v,fs,factor),down=factor,axis=0)[span:span+len(x)]
    if not np.isfinite(y).all():raise ValueError('nonfinite render')
    return y
DESIGNS=[('4x_blackman',4,40,.45,.475,None),('4x_kaiser10',4,40,.45,.475,10),('8x_blackman',8,40,.45,.475,None),('16x_ref',16,160,.47,.49,12),('32x_ref',32,160,.47,.49,12)]
def compare(y,ref):
    scale=rms(ref)/max(rms(y),1e-15)
    return {'relative_error_db':db(rms(y-ref)/max(rms(ref),1e-15)),'rms_matched_error_db':db(rms(y*scale-ref)/max(rms(ref),1e-15)),'gain_delta_db':db(rms(y)/max(rms(ref),1e-15))}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=pathlib.Path);p.add_argument('--manifest',type=pathlib.Path);p.add_argument('--skip-tones',action='store_true');a=p.parse_args();rows=[];audio=[]
    def evaluate(x,fs,sl):
        ys=[render(x,fs,*d[1:])[sl] for d in DESIGNS];ref=ys[-1]
        return [compare(y,ref) for y in ys]
    if not a.skip_tones:
        for fs in (44100,48000,96000):
            t=np.arange(fs//4+fs//8+512)/fs
            for freqs in ((1000,),(7008,),(17008,),(1000,11008),(7008,11008),(15008,17008)):
                for amp in (.1,.5,.9):
                    x=sum(amp/len(freqs)*np.sin(2*np.pi*f*t) for f in freqs)
                    rows.append({'fs':fs,'frequencies':freqs,'amp':amp,'metrics':evaluate(x,fs,slice(fs//4,fs//4+fs//8))})
    if a.manifest:
        seen=set()
        for item in json.loads(a.manifest.read_text())['inputs']:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('invalid fingerprint')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if len(x)<fs or not np.isfinite(x).all():raise ValueError('invalid audio')
            center=len(x)//2;start=center-fs//2;v=x[start:start+fs]
            audio.append({'id':item['id'],'stage':item['stage'],'fs':fs,'start_frame':start,'metrics':evaluate(v,fs,slice(fs//4,3*fs//4))})
    a.output.write_text(json.dumps({'schema':1,'designs':DESIGNS,'tones':rows,'audio':audio,'limits':'Offline higher-rate reference is not ideal ground truth. Differences include bandwidth, phase and residual aliasing; not pure alias measurements. Same nonlinear transfer/DC law, compensated alignment. Reference convergence assessed separately. No native or listening claim.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
