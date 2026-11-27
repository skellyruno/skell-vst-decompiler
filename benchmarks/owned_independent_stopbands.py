"""Screen independent interpolation/decimation filters at fixed 40-sample latency.
Offline original math only. Compare linear image/stopband and nonlinear residual separately.
"""
import argparse,json,pathlib
import numpy as np
from scipy.signal import firwin,freqz,upfirdn,lfilter

def db(x):return float(20*np.log10(max(float(x),1e-15)))
def filt(c,beta):return firwin(161,c/4,fs=1.,window='blackman' if beta is None else ('kaiser',beta))
def spectral(x,fs,hz):
 n=len(x);z=np.abs(np.fft.rfft(x))**2;z[1:len(z)-(n%2==0)]*=2;k=round(hz*n/fs);f=z[k];z[::k]=0;return [db(np.sqrt(2*f)/n),db(np.sqrt(z.sum())/n)]
def shape(x,fs):
 x=np.clip(x,-8,8);d=10**.6;x=np.tanh(d*(x+.12*x*x))/np.tanh(d);p=np.exp(-2*np.pi*5/(4*fs));return lfilter([1,-1],[1,-p],x)
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();u=[(.45,None),(.44,8),(.45,8),(.46,8),(.45,10)];d=[(.475,None),(.465,8),(.475,8),(.485,8),(.475,10)];designs=[(x,y) for x in u for y in d];rows=[];linear=[]
 for c,b in u+d:
  h=filt(c,b);w,H=freqz(h,worN=32768,fs=4.);linear.append(dict(cutoff=c,beta=b,passband_min_db=db(np.min(np.abs(H[w<=.4]))),stopband_max_db=db(np.max(np.abs(H[w>=.55]))),nyquist_db=db(abs(H[np.argmin(abs(w-.5))]))))
 for fs in (44100,48000,96000):
  t=np.arange(fs//2+fs//4+256)/fs
  for hz in (1000,3004,11004,17004,20004):
   for amp in (.1,.5,.9):
    x=amp*np.sin(2*np.pi*hz*t);metrics=[]
    for uc,ub in u:
     v=shape(upfirdn(4*filt(uc,ub),x,up=4),fs)
     for dc,dbeta in d:
      y=upfirdn(filt(dc,dbeta),v,down=4)[40:40+len(x)];metrics.append(spectral(y[fs//2:fs//2+fs//4],fs,hz))
    if not np.isfinite(metrics).all():raise RuntimeError('nonfinite')
    rows.append(dict(fs=fs,hz=hz,amp=amp,metrics=metrics))
 a.output.write_text(json.dumps(dict(schema=1,designs=designs,linear=linear,rows=rows,limits='Offline FIR screen. Linear stopband >= .55 cycles/base sample, passband <= .4. Nonlinear nonharmonic residual excludes harmonic-coincident aliases and DC. No native or subjective claim.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
