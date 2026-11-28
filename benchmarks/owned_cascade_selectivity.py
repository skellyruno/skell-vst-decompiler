"""Offline stage-filter screening; independently implemented, no vendor processing."""
import argparse,json,pathlib
import numpy as np
from scipy.signal import firwin,remez,upfirdn,lfilter

def db(x):return float(20*np.log10(max(float(x),1e-15)))
def black(n,fc):return firwin(n,fc,fs=1.,window='blackman')
def hb(h):
    h=h.copy();j=np.arange(len(h))-(len(h)-1)//2;h[(j!=0)&(j%2==0)]=0;return h/h.sum()
def eq(n,p,s,w):
    h=remez(n,[0,p,s,.5],[1,0],weight=[1,w],fs=1.,maxiter=100);return h/h.sum()
def filters():
    yield 'blackman_65_33',(black(65,.225),black(65,.2375),hb(black(33,.25)))
    for n,m in ((73,17),(65,33),(57,49),(49,65)):
        for p,s,w in ((.205,.275,1),(.215,.275,3),(.225,.275,10)):
            yield f'eq_{n}_{m}_{p}_{s}_{w}',(eq(n,p,s,w),eq(n,min(.235,p+.0125),s,1),hb(eq(m,.19,.31,1)))
def shape(v,fs):
    v=np.clip(v,-8,8);d=10**.6;v=np.tanh(d*(v+.12*v*v))/np.tanh(d);p=np.exp(-2*np.pi*5/(4*fs));return lfilter([1,-1],[1,-p],v)
def baseline(x,fs):
    v=upfirdn(4*black(161,.1125),x,up=4);return upfirdn(black(161,.11875),shape(v,fs),down=4)[40:40+len(x)]
def cascade(x,fs,h):
    u,d,b=h;v=upfirdn(2*u,x,up=2);v=upfirdn(2*b,v,up=2);v=upfirdn(b,shape(v,fs),down=2);return upfirdn(d,v,down=2)[40:40+len(x)]
def spec(y,fs,hz):
    n=len(y);z=np.abs(np.fft.rfft(y))**2;z[1:len(z)-(n%2==0)]*=2;k=round(hz*n/fs);fund=z[k];z[::k]=0;return [db(np.sqrt(2*fund)/n),db(np.sqrt(z.sum())/n)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();designs=list(filters());rows=[]
    for name,(u,d,b) in designs:
        assert (len(u)-1)//2+(len(b)-1)//4==40 and len(u)==len(d)
        assert all(np.isfinite(h).all() and abs(h.sum()-1)<1e-12 for h in (u,d,b))
    for fs in (44100,48000,96000):
        t=np.arange(fs//2+fs//4+256)/fs
        for hz in (1000,3004,11004,17004,20004):
            for amp in (.1,.5,.9):
                x=amp*np.sin(2*np.pi*hz*t);i=fs//2;j=i+fs//4
                metrics=[spec(baseline(x,fs)[i:j],fs,hz)]+[spec(cascade(x,fs,h)[i:j],fs,hz) for _,h in designs]
                if not np.isfinite(metrics).all():raise RuntimeError('nonfinite metrics')
                rows.append({'fs':fs,'hz':hz,'amp':amp,'metrics':metrics})
    a.output.write_text(json.dumps({'schema':1,'order':['single_stage_450_475']+[n for n,_ in designs],'rows':rows,'limits':'Offline FIR screen, all designs 40 sample alignment. Nonharmonic residual excludes harmonic-coincident aliases and DC. No native implementation, CPU or listening result.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
