"""Offline supported-host capture. Native fixtures by default; no vendor binary is bundled.

Run only installed, authorized VST3 effects on a compatible Windows x64 machine.
Process isolation is crash containment, NOT a security sandbox.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import time
import re
import subprocess
import sys

import numpy as np
import soundfile as sf
from .reference_lab import digest, RATES

BLOCKS=(64,128,256,512,1024,2048,4096)
FIXTURES={'Gain':{'gain_db':(-24,12)},'Compressor':{'threshold_db':(-60,0),'ratio':(1,20),'attack_ms':(.1,200),'release_ms':(5,1500)},'Delay':{'delay_seconds':(.001,1),'feedback':(0,.9),'mix':(0,1)}}
SHA=re.compile(r'[a-f0-9]{64}\Z')
ID=re.compile(r'[A-Za-z0-9_-]{1,64}\Z')


def bundle_hash(path):
    """Single-file SHA or deterministic file-list digest of a VST3 bundle."""
    p=Path(path)
    if p.suffix.lower()!='.vst3' or p.is_symlink():raise ValueError('Expected real .vst3 file or bundle')
    if p.is_file():return digest(p)
    if not p.is_dir():raise ValueError('Plugin path unavailable')
    rows=[];total=0
    for f in sorted(p.rglob('*')):
        if f.is_symlink():raise ValueError('Symlink in plugin bundle')
        if f.is_file():
            total+=f.stat().st_size
            if len(rows)>=10000 or total>2*1024**3:raise ValueError('Bundle exceeds limits')
            rows.append([f.relative_to(p).as_posix(),digest(f)])
    if not rows:raise ValueError('Empty bundle')
    return hashlib.sha256(json.dumps(rows,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()


def windows_module_path(path):
    """Resolve the standard x64 VST3 entry without moving or rewriting the bundle."""
    p=Path(path)
    if p.suffix.lower()!='.vst3' or p.is_symlink():raise ValueError('Invalid VST3 path')
    if p.is_file():return p
    if not p.is_dir():raise ValueError('Plugin path unavailable')
    module=p/'Contents'/'x86_64-win'/p.name
    if any(q.is_symlink() for q in (p/'Contents',module.parent,module)) or not module.is_file():raise ValueError('Standard Windows x64 VST3 module missing')
    return module


def validate(spec, authorized=False):
    if not isinstance(spec,dict) or spec.get('backend') not in ('fixture','installed_vst3'):raise ValueError('Unknown backend')
    params=spec.get('parameters')
    if not isinstance(params,dict) or len(params)>128:raise ValueError('Invalid parameters')
    for k,v in params.items():
        if not isinstance(k,str) or not ID.fullmatch(k) or type(v) not in (int,float,str,bool) or (type(v) in (int,float) and not math.isfinite(v)) or (isinstance(v,str) and len(v)>256):raise ValueError('Invalid parameter')
    if spec.get('backend')=='fixture':
        ranges=FIXTURES.get(spec.get('name'))
        if ranges is None or set(params)!=set(ranges) or any(type(params[k]) not in (float,int) or not lo<=params[k]<=hi for k,(lo,hi) in ranges.items()):raise ValueError('Invalid fixture configuration')
    else:
        if not authorized or spec.get('authorization')!='installed_and_licensed' or spec.get('purpose') not in ('owned_fixture','reference'):raise ValueError('Explicit authorized purpose required')
        if platform.system()!='Windows' or platform.machine().lower() not in ('amd64','x86_64') or sys.maxsize<=2**32:raise ValueError('Installed VST3 adapter requires Windows x64 Python')
        path=Path(spec.get('path',''))
        if not path.is_absolute() or not isinstance(spec.get('sha256'),str) or not SHA.fullmatch(spec['sha256']) or not isinstance(spec.get('version'),str) or not spec['version'].strip():raise ValueError('Missing installed identity')
        expected=spec.get('expected_normalized')
        if not isinstance(expected,dict) or set(expected)!=set(params) or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in expected.values()):raise ValueError('Expected normalized readback required for each requested control')
        if bundle_hash(path)!=spec['sha256']:raise ValueError('Installed plugin fingerprint mismatch')
    if spec.get('block_size') not in BLOCKS or type(spec['block_size']) is not int:raise ValueError('Unsupported block size')
    if not isinstance(spec.get('target_stage'),str) or not spec['target_stage'].strip():raise ValueError('Missing target stage')
    return spec


def normalized_readback(fx,expected):
    if len(fx.parameters)>2048:raise ValueError('Parameter inventory too large')
    values={k:float(v.raw_value) for k,v in sorted(fx.parameters.items())}
    if any(not math.isfinite(v) or not 0<=v<=1 for v in values.values()):raise ValueError('Invalid normalized parameter readback')
    if any(k not in values or abs(values[k]-v)>1e-5 for k,v in expected.items()):raise ValueError('Requested control failed normalized readback')
    return values


def capture(root,case,spec,output,authorized=False):
    """One isolated render, no padding/truncation or inferred latency correction."""
    validate(spec,authorized);root,output=Path(root),Path(output)
    if output.exists():raise FileExistsError(output)
    m=json.loads((root/'manifest.json').read_text());fs=m['sample_rate']
    rows=[r for r in m['cases'] if r['id']==case]
    if m.get('schema')!=1 or fs not in RATES or not ID.fullmatch(case) or len(rows)!=1:raise ValueError('Invalid case')
    row=rows[0];source=root/(case+'.wav')
    if row['file']!=source.name or digest(source)!=row['sha256']:raise ValueError('Source hash mismatch')
    info=sf.info(source)
    if info.samplerate!=fs or info.channels!=2 or info.frames!=row['frames'] or not 64<=info.frames<=120*fs:raise ValueError('Invalid source dimensions')
    x,_=sf.read(source,dtype='float32',always_2d=True)
    if not np.isfinite(x).all() or np.max(abs(x))>1.000001:raise ValueError('Invalid stimulus')
    import pedalboard as pb
    if pb.__version__!='0.9.23':raise ValueError('Use the tested Pedalboard 0.9.23 host version')
    external=spec['backend']=='installed_vst3'
    if external:
        module=windows_module_path(spec['path']);module_sha=digest(module)
        fx=pb.load_plugin(str(module),plugin_name=spec.get('plugin_name'),initialization_timeout=10.)
        if not fx.is_effect or fx.is_instrument:raise ValueError('Only audio effects supported')
        if any(k not in fx.parameters for k in spec['parameters']):raise ValueError('Unknown plugin parameter')
        for k,v in spec['parameters'].items():setattr(fx,k,v)
        readback=normalized_readback(fx,spec['expected_normalized'])
        settings_readback=readback
        plugin_name=str(fx.name);version=str(fx.version);binary_sha=spec['sha256']
        if version!=spec['version']:raise ValueError('Installed version mismatch')
    else:
        fx=getattr(pb,spec['name'])(**spec['parameters'])
        readback={k:float(getattr(fx,k)) for k in spec['parameters']};settings_readback=readback
        plugin_name='Pedalboard '+spec['name'];version=pb.__version__;binary_sha=None
    start=time.perf_counter()
    y=fx.process(np.ascontiguousarray(x.T),fs,buffer_size=spec['block_size'],reset=True).T
    elapsed=time.perf_counter()-start
    if external:
        after=normalized_readback(fx,spec['expected_normalized'])
        if after.keys()!=readback.keys() or any(not math.isfinite(v) or abs(v-readback[k])>1e-6 for k,v in after.items()):raise ValueError('Parameter readback changed after processing')
    if y.shape!=x.shape or not np.isfinite(y).all() or np.max(abs(y))>64:raise ValueError('Invalid or buffered output; no silent length correction')
    if digest(source)!=row['sha256'] or (external and (bundle_hash(spec['path'])!=binary_sha or digest(module)!=module_sha)):raise ValueError('Input changed during render')
    output.mkdir(parents=True,exist_ok=False)
    wet=output/'render.wav';sf.write(wet,y,fs,subtype='FLOAT')
    meta={'plugin':plugin_name,'version':version,'settings':json.dumps({'requested':spec['parameters'],'readback':settings_readback},sort_keys=True),'source_sha256':row['sha256'],'render_sha256':digest(wet),'offset_samples':0,'target_stage':spec['target_stage'],'evidence':'EXEC: reference' if external and spec['purpose']=='reference' else 'EXEC: fixture','host':'Pedalboard '+pb.__version__,'backend':spec['backend'],'binary_sha256':binary_sha,'host_module_sha256':module_sha if external else None,'sample_rate':fs,'frames':len(y),'block_size':spec['block_size'],'reset':True,'parameter_readback':readback,'offline_process_seconds':elapsed,'alignment_status':'host_compensated_unverified' if external else 'fixture_no_extra_offset','reported_latency_samples':int(fx.reported_latency_samples) if external else None,'latency_note':'Pedalboard compensates reported latency; actual alignment not independently measured. No additional offset applied.'}
    (output/'metadata.json').write_text(json.dumps(meta,indent=2,allow_nan=False)+'\n');return meta


def run_matrix(root,plan,output,*,authorized=False,timeout=60):
    """Fresh child process per job; preserve failures, never overwrite a run."""
    if not isinstance(plan,list) or not 1<=len(plan)<=128 or type(timeout) is not int or not 5<=timeout<=300:raise ValueError('Invalid matrix budget')
    ids=set()
    for job in plan:
        if not isinstance(job,dict) or set(job)!= {'id','case','spec'} or not isinstance(job['case'],str):raise ValueError('Invalid matrix job')
        ident=job['id']
        if not isinstance(ident,str) or not ID.fullmatch(ident) or ident.lower() in ('results','con','prn','aux','nul',*(f'com{i}' for i in range(1,10)),*(f'lpt{i}' for i in range(1,10))) or ident.lower() in ids or not ID.fullmatch(job['case']):raise ValueError('Invalid job identity')
        ids.add(ident.lower());validate(job['spec'],authorized)
    root,output=Path(root).resolve(),Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    results=[]
    for job in plan:
        folder=output/job['id'];specfile=output/(job['id']+'.json')
        specfile.write_text(json.dumps(job['spec'],indent=2,allow_nan=False)+'\n')
        args=[sys.executable,'-m','skell_vst_decompiler.host_capture','capture',str(root),job['case'],str(specfile),str(folder)]
        if authorized:args.append('--authorized-installed')
        try:
            p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False)
            if p.returncode!=0:raise RuntimeError('Child exited '+str(p.returncode)+': '+p.stderr[-1200:])
            meta=json.loads((folder/'metadata.json').read_text())
            if meta['render_sha256']!=digest(folder/'render.wav') or meta['source_sha256']!=digest(root/(job['case']+'.wav')) or meta['block_size']!=job['spec']['block_size'] or meta['target_stage']!=job['spec']['target_stage'] or meta['backend']!=job['spec']['backend']:raise ValueError('Child output identity mismatch')
            result={'id':job['id'],'case':job['case'],'status':'captured','metadata':meta}
        except (subprocess.TimeoutExpired,RuntimeError,ValueError,OSError,KeyError) as exc:
            result={'id':job['id'],'case':job['case'],'status':'failed','error':str(exc)[:1500]}
        results.append(result)
        temp=output/'results.tmp'
        temp.write_text(json.dumps(results,indent=2,allow_nan=False)+'\n');temp.replace(output/'results.json')
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    c=s.add_parser('capture');c.add_argument('root');c.add_argument('case');c.add_argument('spec');c.add_argument('output');c.add_argument('--authorized-installed',action='store_true')
    m=s.add_parser('matrix');m.add_argument('root');m.add_argument('plan');m.add_argument('output');m.add_argument('--authorized-installed',action='store_true');m.add_argument('--timeout',type=int,default=60)
    h=s.add_parser('fingerprint');h.add_argument('path');a=p.parse_args()
    load=lambda f:json.loads(Path(f).read_text())
    if a.cmd=='fingerprint':r={'sha256':bundle_hash(a.path)}
    elif a.cmd=='capture':r=capture(a.root,a.case,load(a.spec),a.output,a.authorized_installed)
    else:r=run_matrix(a.root,load(a.plan),a.output,authorized=a.authorized_installed,timeout=a.timeout)
    print(json.dumps(r,indent=2,allow_nan=False));return int(isinstance(r,list) and any(x['status']!='captured' for x in r))


if __name__=='__main__':raise SystemExit(main())
