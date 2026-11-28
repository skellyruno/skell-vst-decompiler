"""Validate owner-exported isolated WAV observations, without loading plugins."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from .topology_gate import screen, candidate_gate, rms

KEYS=('base','repeat','half','other','sum','alternate_prefix','shifted','quiet_left','loud_right','quiet_right','loud_left')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>1048576:raise ValueError('invalid metadata file')
    return json.loads(path.read_text(encoding='utf-8'))


def audio(path,fs,n,sha=None):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>32*1024*1024:raise ValueError('invalid WAV file')
    before=digest(path)
    if sha is not None and before!=sha:raise ValueError('audio digest mismatch: '+path.name)
    info=sf.info(path)
    if info.format not in ('WAV','WAVEX') or info.samplerate!=fs or info.frames!=n or info.channels!=2:raise ValueError('format or length mismatch: '+path.name)
    x,_=sf.read(path,dtype='float64',always_2d=True)
    if not np.isfinite(x).all() or np.max(abs(x))>64 or digest(path)!=before:raise ValueError('invalid or changed audio')
    return x,before


def sources(folder):
    root=Path(folder);path=root/'manifest.json';m=read_json(path);fs=m['sample_rate']
    if m['schema']!=1 or fs not in (44100,48000,96000) or len(m['cases'])!=11 or m['suffix_start']!=fs//2 or m['shift_samples']!=fs//20:raise ValueError('invalid topology manifest')
    rows={r['id']:r for r in m['cases']}
    if set(rows)!=set(KEYS):raise ValueError('missing probe')
    x={};hashes={}
    for i,k in enumerate(KEYS):
        r=rows[k];n=fs if i<7 else 2*fs
        if r['file']!=k+'.wav' or r['frames']!=n or r['channels']!=2:raise ValueError('invalid probe manifest row')
        x[k],hashes[k]=audio(root/r['file'],fs,n,r['sha256'])
    # File rounding is exact float32; sum is compared in source precision.
    eq=np.array_equal
    if not (eq(x['base'],x['repeat']) and eq(.5*x['base'],x['half']) and eq((x['base']+x['other']).astype(np.float32),x['sum']) and eq(x['base'][fs//2:],x['alternate_prefix'][fs//2:]) and eq(x['base'][:-fs//20],x['shifted'][fs//20:]) and not np.any(x['shifted'][:fs//20]) and eq(x['quiet_left'],x['quiet_right'][:,::-1]) and eq(x['loud_right'],x['loud_left'][:,::-1]) and eq(x['quiet_left'][:,0],x['loud_right'][:,0]) and not np.any(x['quiet_left'][:,1]) and not np.any(x['quiet_right'][:,0])):raise ValueError('probe relation mismatch')
    if max(np.max(abs(a)) for a in x.values())>1:raise ValueError('unexpected source peak')
    return fs,x,hashes


def declaration(path):
    d=read_json(Path(path))
    for k in ('plugin','version','host','settings','target_stage'):
        if not isinstance(d.get(k),str) or not d[k].strip() or len(d[k])>8192:raise ValueError('missing declaration: '+k)
    for k in ('authorized','isolated','fresh_reset','no_normalization','same_settings'):
        if d.get(k) is not True:raise ValueError('required owner declaration: '+k)
    if d.get('alignment') not in ('unverified','owner_verified_active_timeline') or type(d.get('reported_latency_samples')) is not int or not 0<=d['reported_latency_samples']<=192000:raise ValueError('invalid latency declaration')
    if d['alignment']=='owner_verified_active_timeline' and (not isinstance(d.get('alignment_note'),str) or not d['alignment_note'].strip()):raise ValueError('active alignment evidence note required')
    return d


def seal(probes,wet,decl,out):
    """Create manifest after export, never overwrite. Declaration is not authentication."""
    fs,x,sh=sources(probes);d=declaration(decl);root=Path(wet);rh={}
    for k in (*KEYS,'bypass'):
        _,rh[k]=audio(root/(k+'.wav'),fs,len(x['base' if k=='bypass' else k]))
    manifest=dict(schema=1,scope='owner_declared_manual_capture',sample_rate=fs,declaration=d,source_sha256=sh,render_sha256=rh)
    with Path(out).open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2,allow_nan=False);f.write('\n')
    return manifest


def analyze(probes,wet,session):
    fs,x,sh=sources(probes);m=read_json(Path(session));d=m['declaration'];root=Path(wet)
    if m['schema']!=1 or m['scope']!='owner_declared_manual_capture' or m['sample_rate']!=fs or m['source_sha256']!=sh or set(m['render_sha256'])!=set((*KEYS,'bypass')):raise ValueError('capture manifest mismatch')
    for k in ('authorized','isolated','fresh_reset','no_normalization','same_settings'):
        if d.get(k) is not True:raise ValueError('invalid declaration')
    for k in ('plugin','version','host','settings','target_stage'):
        if not isinstance(d.get(k),str) or not d[k].strip():raise ValueError('missing declaration')
    if d.get('alignment') not in ('unverified','owner_verified_active_timeline') or type(d.get('reported_latency_samples')) is not int or not 0<=d['reported_latency_samples']<=192000:raise ValueError('invalid alignment')
    y={}
    for k in (*KEYS,'bypass'):
        y[k],_=audio(root/(k+'.wav'),fs,len(x['base' if k=='bypass' else k]),m['render_sha256'][k])
    bypass=float(np.max(abs(y['bypass']-x['base'])))
    result=dict(scope='owner-declared, not authenticated; short aligned observations only',plugin=d['plugin'],sample_rate=fs,bypass_peak_error=bypass,peak_by_case={k:float(np.max(abs(y[k]))) for k in KEYS},reported_latency_samples=d['reported_latency_samples'])
    reasons=[]
    if bypass>2e-6:reasons.append('bypass export differs from original stimulus')
    if d['alignment']!='owner_verified_active_timeline' or not str(d.get('alignment_note','')).strip():reasons.append('active timeline alignment not independently established')
    if d['reported_latency_samples']!=0:reasons.append('nonzero reported latency needs separate calibrated capture workflow')
    if any(v>1.000001 for v in result['peak_by_case'].values()):reasons.append('output above full scale; check export headroom')
    if reasons:return dict(result,status='REVIEW_REQUIRED',reasons=reasons)
    diag=screen(np.stack([y[k] for k in KEYS[:6]]),fs//2)
    shift=fs//20;shift_err=rms(y['shifted'][shift:]-y['base'][:-shift])/max(rms(y['base'][:-shift]),1e-12)
    pairs=[]
    for c,a,b in ((0,'quiet_left','loud_right'),(1,'quiet_right','loud_left')):
        v,w=y[a][-fs:,c],y[b][-fs:,c];scale=max(rms(v),rms(w))
        pairs.append(dict(channel=c,baseline_rms=rms(v),changed_rms=rms(w),difference_rms=rms(v-w),relative_difference=rms(v-w)/scale if scale>1e-9 else None))
    gate=candidate_gate(diag,shift_err)
    return dict(result,status='SCREENED_OWNER_DECLARED' if gate['action']=='SCREENED' else 'RECAPTURE',diagnostic=diag,shift_relative=shift_err,candidates=gate,stereo=pairs,note='No automatic alignment, model recovery, or inference of unique architecture. Bypass agreement does not prove active-path alignment. Long tails require separate probes.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    a=s.add_parser('seal');a.add_argument('probes');a.add_argument('wet');a.add_argument('declaration');a.add_argument('session')
    a=s.add_parser('analyze');a.add_argument('probes');a.add_argument('wet');a.add_argument('session')
    a=p.parse_args();r=seal(a.probes,a.wet,a.declaration,a.session) if a.cmd=='seal' else analyze(a.probes,a.wet,a.session);print(json.dumps(r,indent=2,allow_nan=False))
