"""Offline release-bound oracle, not a new streaming limiter.
The pairwise dual bound uses only inequalities satisfied by the scheduled gains.
"""
import argparse,hashlib,json,pathlib
import numpy as np
import soundfile as sf
from scipy.optimize import linprog
from scipy.signal import lfilter
from alias_reference import render,db
N=17; CEILING=10**(-1/20)
def kernel():
    t=np.arange(N)[None,:]-8-np.arange(4)[:,None]/4
    h=np.sinc(t)*(.42+.5*np.cos(np.pi*t/9)+.08*np.cos(2*np.pi*t/9));h[0]=0;h[0,8]=1
    return h/h.sum(axis=1,keepdims=True)
def cap(slope,cost,ceiling=CEILING):
    return float(np.clip((ceiling-cost)/slope,0,1)) if slope>0 else float(cost<=ceiling)
def previous(w,poles):
    rise=1-np.cumprod(np.r_[1.,poles[:0:-1]])[::-1]
    return max(cap(np.maximum(w,0).sum(),0),cap(max(0,np.cumsum(w).max()),np.dot(np.maximum(-w,0),rise)))
def pair(w,poles):
    v=w.copy();cost=0.
    # For positive w_j and negative w_i, i<j, replace lambda*g_j
    # with lambda*(P*g_i+1-P), P=product of recovery poles i+1..j.
    # This cancels opposite weights without assuming equal gains.
    for j in range(N-1,0,-1):
        if v[j]<=0:continue
        p=1.
        for i in range(j-1,-1,-1):
            p*=poles[i+1]
            if v[i]<0:
                lam=min(v[j],-v[i]/p);v[j]-=lam;v[i]+=lam*p;cost+=lam*(1-p)
                if v[j]<=0:break
    return cap(np.maximum(v,0).sum(),cost)
def lp(w,poles,g):
    A=np.zeros((N-1,N));i=np.arange(N-1);A[i,i]=-poles[1:];A[i,i+1]=1
    result=linprog(-w,A_ub=A,b_ub=1-poles[1:],bounds=[(0,g)]*N,method='highs')
    if not result.success:raise RuntimeError(result.message)
    return -float(result.fun)
def detector(x,fs):
    x=np.clip(x,-32,32);r=np.exp(-2*np.pi*120/fs);e=np.exp(-1/(.020*fs));lo=lfilter([1-r],[1,-r],x,axis=0)
    low=lfilter([1-e],[1,-e],np.sum(lo*lo,axis=1));full=lfilter([1-e],[1,-e],np.sum(x*x,axis=1))
    fast=np.exp(-1/(.001*fs));slow=np.exp(-1/(.060*fs));return fast+(slow-fast)*np.clip((low/(full+1e-20)-.15)/.65,0,1)
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();rows=[];seen=set();h=kernel();rng=np.random.default_rng(719)
    # Random windows independent of selected recording windows.
    for i in range(128):
        w=rng.normal(0,.4,N);r=np.exp(-1/(.001*rng.uniform(1,60,N)*48000));old=previous(w,r);new=max(old,pair(w,r));z=lp(w,r,new)
        if z>CEILING+2e-8:raise RuntimeError('unsafe dual cap')
        rows.append(dict(kind='random',old=old,new=new,lp_peak=z))
    for item in json.loads(a.manifest.read_text())['inputs']:
        src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
        if digest!=item['sha256'] or digest in seen:raise ValueError('fingerprint mismatch')
        seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
        if len(x)<fs or not np.isfinite(x).all():raise ValueError('invalid audio')
        if x.shape[1]==1:x=np.repeat(x,2,axis=1)
        v=x[len(x)//2-fs//2:len(x)//2+fs//2];y=render(v,fs,4,40,.45,.475);r=detector(y,fs)
        # One strongest sample per disjoint quarter of the middle half-second.
        for group in np.array_split(np.arange(fs//4,3*fs//4),4):
            at=int(group[np.argmax(np.max(np.abs(y[group]),axis=1))]);seg=y[at-8:at+9];poles=r[at-8:at+9]
            weights=[sign*phase*seg[:,c] for phase in h for c in (0,1) for sign in (1,-1)]
            old=min(previous(w,poles) for w in weights);new=min(max(previous(w,poles),pair(w,poles)) for w in weights)
            z=max(lp(w,poles,new) for w in weights)
            if z>CEILING+2e-8:raise RuntimeError('unsafe audio dual cap')
            rows.append(dict(kind='audio',id=item['id'],stage=item['stage'],frame=at,old=old,new=new,lp_peak=z))
    a.output.write_text(json.dumps(dict(schema=1,rows=rows,ceiling=CEILING,limits='Per-window gain caps, not actual rendered gain or loudness. LP numerical oracle, fixed declared reconstruction kernel; no certified true peak or native performance.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
