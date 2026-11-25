"""Offline public-parameter analysis, never runs a target on the DAW audio thread."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np

MAX_STATE=4*1024*1024


def state_difference(baseline, repeat, changed):
    """Report stable candidate byte locations, not decoded private state semantics."""
    if any(not isinstance(x,bytes) or len(x)>MAX_STATE for x in (baseline,repeat,changed)):
        raise ValueError('Invalid state bytes')
    if len({len(baseline),len(repeat),len(changed)})!=1:
        return {'status':'VARIABLE_LENGTH','lengths':[len(baseline),len(repeat),len(changed)]}
    a,b,c=(np.frombuffer(x,dtype=np.uint8) for x in (baseline,repeat,changed))
    indices=np.flatnonzero((a==b)&(a!=c))
    spans=[];span_count=0;last=-2
    for i in indices:
        i=int(i)
        if i!=last+1:
            span_count+=1
            if span_count<=256:spans.append([i,i+1])
        elif span_count<=256:spans[-1][1]=i+1
        last=i
    return {'status':'CANDIDATE','length':len(a),'unstable_baseline_bytes':int(np.count_nonzero(a!=b)),
            'stable_changed_bytes':int(len(indices)),'spans':spans,'truncated':span_count>256}


def stimuli(fs=48000):
    if fs not in (44100,48000,96000,192000):raise ValueError('Unsupported rate')
    n=fs//5;t=np.arange(n)/fs
    impulse=np.zeros(n,np.float32);impulse[0]=.1
    return {'impulse':impulse,'quiet':(.03*np.sin(2*np.pi*1000*t)).astype(np.float32),
            'loud':(.85*np.sin(2*np.pi*1000*t)).astype(np.float32),
            'high':(.03*np.sin(2*np.pi*9000*t)).astype(np.float32),
            'recovery':(np.where(np.arange(n)<n//2,.85,.03)*np.sin(2*np.pi*1000*t)).astype(np.float32)}


def metrics(x,y):
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    if x.shape!=y.shape or x.ndim!=1 or len(x)<64 or not np.isfinite(y).all():raise ValueError('Invalid render')
    x=x[len(x)//2:];y=y[len(y)//2:]
    gain=np.sqrt(np.mean(y*y)/max(1e-20,np.mean(x*x)))
    # Best scalar residual is only a nonlinear/phase-change clue, not THD.
    scalar=float(np.dot(x,y)/max(1e-20,np.dot(x,x)))
    return {'gain':float(gain),'residual':float(np.sqrt(np.mean((y-scalar*x)**2))), 'peak':float(np.max(abs(y)))}


def describe(probes, rendered):
    if set(probes)!=set(rendered):raise ValueError('Incomplete probe set')
    impulse=np.asarray(rendered['impulse'])
    if impulse.shape!=probes['impulse'].shape or not np.isfinite(impulse).all():raise ValueError('Invalid impulse')
    hits=np.flatnonzero(abs(impulse)>1e-6)
    recovery=np.asarray(rendered['recovery']);quiet=np.asarray(rendered['quiet'])
    if recovery.shape!=probes['recovery'].shape or not np.isfinite(recovery).all():raise ValueError('Invalid recovery probe')
    start=len(quiet)//2; a=quiet[start:start+64]; b=recovery[start:start+64]
    memory=float(np.sqrt(np.mean((a-b)**2)/max(1e-20,np.mean(a*a))))
    return {'first_arrival':int(hits[0]) if len(hits) else None,'impulse_nonzero':int(len(hits)),
            'recovery_difference':memory,**{k:metrics(probes[k],rendered[k]) for k in ('quiet','loud','high')}}


def behavior_candidate(r):
    """Conservative probe-based ranking of observable behavior, not source recovery."""
    q,l,h=(r[k]['gain'] for k in ('quiet','loud','high'))
    if r['first_arrival'] is None or q<1e-6:return 'unresolved'
    if r['first_arrival']>0 and r['impulse_nonzero']==1:return 'delay'
    if r['impulse_nonzero']>2 and h<q*.9:return 'filter'
    if l<q*.85:return 'level_dependent_memory' if r['recovery_difference']>.02 else 'level_dependent_no_observed_memory'
    if abs(l-q)<.01 and abs(h-q)<.01 and r['quiet']['residual']<1e-4 and abs(q-1)>.02:return 'gain'
    return 'unresolved'


def installed_capture(spec):
    """Explicit installed, licensed Windows VST3 only; no arbitrary archived DLL loading."""
    import platform
    from .host_capture import bundle_hash, windows_module_path
    if platform.system()!='Windows' or platform.machine().lower() not in ('amd64','x86_64') or sys.maxsize<=2**32:
        raise ValueError('Windows x64 host required')
    if spec.get('authorization')!='installed_and_licensed' or spec.get('purpose') not in ('owned_fixture','reference'):raise ValueError('Authorized installed purpose required')
    path=Path(spec['path'])
    if not path.is_absolute() or bundle_hash(path)!=spec['sha256']:raise ValueError('Source identity mismatch')
    module=windows_module_path(path);module_sha=hashlib.sha256(module.read_bytes()).hexdigest()
    import pedalboard as pb
    if pb.__version__!='0.9.23':raise ValueError('Pinned host required')
    fx=pb.load_plugin(str(module),plugin_name=spec.get('plugin_name'),initialization_timeout=10.)
    if not fx.is_effect or fx.is_instrument or str(fx.version)!=spec['version']:raise ValueError('Wrong plugin kind/version')
    if not 0<len(fx.parameters)<=2048:raise ValueError('Invalid parameter inventory')
    key=spec.get('parameter');value=spec.get('normalized')
    if key is not None:
        if key not in fx.parameters or type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1:raise ValueError('Invalid parameter request')
        fx.parameters[key].raw_value=value
    readback={k:float(v.raw_value) for k,v in fx.parameters.items()}
    if any(not math.isfinite(v) or not 0<=v<=1 for v in readback.values()):raise ValueError('Invalid readback')
    if key is not None and abs(readback[key]-value)>1e-5:raise ValueError('Parameter quantized or rejected; use supported normalized points')
    # Read only; never restore arbitrary state bytes.
    raw=bytes(fx.raw_state)
    if len(raw)>MAX_STATE:raise ValueError('State too large')
    fs=spec.get('sample_rate',48000);probes=stimuli(fs);rendered={}
    for name,x in probes.items():
        stereo=np.stack((x,x));y=fx.process(stereo,fs,buffer_size=256,reset=True)
        if y.shape!=stereo.shape or not np.isfinite(y).all():raise ValueError('Invalid host render')
        rendered[name]=y[0]
    after={k:float(v.raw_value) for k,v in fx.parameters.items()}
    if bundle_hash(path)!=spec['sha256'] or hashlib.sha256(module.read_bytes()).hexdigest()!=module_sha or after!=readback:raise ValueError('Source or parameter readback changed')
    result={'binary_sha256':spec['sha256'],'version':str(fx.version),'host_module_sha256':module_sha,'parameters':readback,'metrics':describe(probes,rendered),
            'state_sha256':hashlib.sha256(raw).hexdigest(),'reported_latency':int(fx.reported_latency_samples),'alignment':'host_compensated_unverified'}
    result['behavior_candidate']=behavior_candidate(result['metrics'])
    return result,raw


def run_sweep(spec, key, values, timeout=90):
    """One fresh child per setting plus repeated baseline. Private temp state only."""
    if not isinstance(values,list) or not 2<=len(values)<=16 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in values) or len(set(values))!=len(values):raise ValueError('Invalid sweep points')
    if not isinstance(key,str) or not key or len(key)>256 or type(timeout) is not int or not 5<=timeout<=300:raise ValueError('Invalid sweep budget')
    rows=[];states=[]
    with tempfile.TemporaryDirectory(prefix='skell-analyzer-') as tmp:
        root=Path(tmp)
        for i,v in enumerate([values[0]]+values):
            job=root/f'{i}.json';out=root/f'{i}.out';state=root/f'{i}.state'
            job.write_text(json.dumps(dict(spec,parameter=key,normalized=v),allow_nan=False))
            try:
                subprocess.run([sys.executable,'-m','skell_vst_decompiler.analyzer_worker','child',str(job),str(out),str(state)],check=True,timeout=timeout,capture_output=True)
                if out.stat().st_size>4*1024*1024 or state.stat().st_size>MAX_STATE:raise ValueError('Child result exceeds bounds')
                row=json.loads(out.read_text());raw=state.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=row['state_sha256'] or row['binary_sha256']!=spec['sha256'] or row['version']!=spec['version'] or abs(row['parameters'][key]-v)>1e-5:raise ValueError('Child identity mismatch')
                rows.append({'value':v,'status':'captured',**row});states.append(raw)
            except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:
                rows.append({'value':v,'status':'failed','error':str(e)[:300]});states.append(None)
        baseline_stable=states[0] is not None and states[1] is not None and rows[0]['parameters']==rows[1]['parameters'] and rows[0]['metrics']==rows[1]['metrics']
        if baseline_stable:
            for i in range(2,len(rows)):
                if states[i] is not None:
                    rows[i]['state_difference']=state_difference(states[0],states[1],states[i])
                    rows[i]['other_changed_controls']=[k for k,v in rows[0]['parameters'].items() if k!=key and rows[i]['parameters'].get(k)!=v]
                    rows[i]['observable_metrics_changed']=rows[i]['metrics']!=rows[0]['metrics']
    return {'parameter':key,'rows':rows,'repeat_metrics_stable':baseline_stable,'note':'Public host keys, not numeric VST3 IDs. State locations are candidates; no private bytes exported. Process isolation is not a security sandbox.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    c=s.add_parser('child');c.add_argument('spec');c.add_argument('output');c.add_argument('state')
    inv=s.add_parser('inventory');inv.add_argument('spec')
    q=s.add_parser('sweep');q.add_argument('spec');q.add_argument('parameter');q.add_argument('values',nargs='+',type=float)
    a=p.parse_args();spec=json.loads(Path(a.spec).read_text())
    if a.mode=='child':
        result,raw=installed_capture(spec);Path(a.state).write_bytes(raw);Path(a.output).write_text(json.dumps(result,allow_nan=False));return 0
    if a.mode=='inventory':
        # Fresh child, identical validation to a sweep; no raw state bytes retained.
        with tempfile.TemporaryDirectory(prefix='skell-inventory-') as tmp:
            root=Path(tmp);job=root/'job.json';out=root/'out.json';state=root/'state.bin'
            job.write_text(json.dumps(dict(spec,parameter=None,normalized=None),allow_nan=False))
            subprocess.run([sys.executable,'-m','skell_vst_decompiler.analyzer_worker','child',str(job),str(out),str(state)],check=True,timeout=90)
            result=json.loads(out.read_text());print(json.dumps(result,indent=2,allow_nan=False));return 0
    result=run_sweep(spec,a.parameter,a.values);print(json.dumps(result,indent=2,allow_nan=False));return int(any(r['status']!='captured' for r in result['rows']))


if __name__=='__main__':raise SystemExit(main())
