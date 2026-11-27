"""Owned-only semantic calibration. Never executes a Windows or vendor binary.
Run from repo root: python benchmarks/owned_context_audio.py --output result.json
Requires local clang, lld-link, a C++ compiler, GNU and LLVM objdump (Linux).
"""
import argparse
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.disasm import disassemble
from skell_vst_decompiler.transfer_triage import raw_decode
from skell_vst_decompiler.window_reconcile import Window, inspect, reconcile_windows
from skell_vst_decompiler.value_flow import scan
from skell_vst_decompiler.scope_consensus import audit_scope

ROLES = {'audio_gain': 'audio_math', 'geometry_scale': 'ui_math',
         'audio_clip': 'audio_math', 'copy_control': 'clear_control',
         'dispatch': 'context_dependent_dispatch', 'audio_route': 'audio_route',
         'ui_route': 'ui_route', 'clip_route': 'audio_route', 'clear_route': 'control_route'}


def run(*args):
    subprocess.run(args, check=True, cwd=ROOT)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def static_fixture(work, opt):
    obj, dll, linkmap = [work / (opt + ext) for ext in ('.obj','.dll','.map')]
    run('clang','--target=x86_64-pc-windows-msvc',opt,'-ffreestanding','-fno-builtin','-c',
        str(ROOT/'tests/fixtures/role_context.c'),'-o',str(obj))
    run('lld-link','/dll','/noentry','/nodefaultlib','/opt:noicf','/timestamp:0',
        '/map:'+str(linkmap),'/out:'+str(dll),str(obj))
    pe=PE(dll); text=pe.section('.text')
    symbols={m[1]:int(m[2],16)-pe.image_base for m in re.finditer(
        r'^\s*0001:[0-9a-fA-F]+\s+(\w+)\s+([0-9a-fA-F]+)\s+',linkmap.read_text(),re.M) if m[1] in ROLES}
    if set(symbols)!=set(ROLES): raise RuntimeError('Missing owned link-map symbols')
    order=sorted(symbols,key=symbols.get)
    windows=[]; streams=[]; raw=[]; rows={}
    for i,name in enumerate(order):
        start=symbols[name]; stop=symbols[order[i+1]] if i+1<len(order) else text.rva+text.virtual_size
        length=stop-start; va=pe.image_base+start
        maps=tuple(raw_decode(pe,start,length,t) for t in ('objdump','llvm-objdump'))
        windows.append(Window(va,va+length,maps))
        streams.append([disassemble(pe,start,length,t) for t in ('objdump','llvm-objdump')])
        raw.append(pe.at_rva(start,length,executable=True))
        evidence=audit_scope(pe,pe.sha256,start,length)
        transfers=inspect(windows[-1])
        rows[name]={'role_from_source':ROLES[name],'scope_bytes':length,'scope_sha256':hashlib.sha256(raw[-1]).hexdigest(),
                    'arithmetic_sites':sum(evidence['fp_families'].values()),
                    'direct_sites':sum(k=='direct' for k,t in transfers.values()),
                    'indirect_sites':sum(k.startswith('indirect_') for k,t in transfers.values())}
    guards,counts=reconcile_windows(windows)
    for i,name in enumerate(order):
        rows[name]['local_transformed_stores']=scan(*streams[i],raw[i],windows[i].start,entries=guards[i])['total']
    same=raw[order.index('audio_gain')]==raw[order.index('geometry_scale')]
    assert same, 'Fixture must have byte-identical gain and geometry windows'
    assert rows['dispatch']['indirect_sites']>=1
    assert rows['audio_gain']['arithmetic_sites']>0
    return {'optimization':opt,'pe_sha256':pe.sha256,'gain_geometry_exact_bytes_equal':same,
            'rows':rows,'window_counts':counts}


def native_routes(work, opt):
    path=work/(opt+'.so')
    run('clang',opt,'-shared','-fPIC',str(ROOT/'tests/fixtures/role_context.c'),'-o',str(path))
    lib=C.CDLL(str(path)); vals=[-1.0,-.5,-.125,0,.125,.5,1.0]
    callback=C.CFUNCTYPE(None,C.POINTER(C.c_float),C.c_uint,C.c_float)
    dispatch=lib.dispatch;dispatch.argtypes=[callback,C.POINTER(C.c_float),C.c_uint,C.c_float];dispatch.restype=None
    cases={'audio_gain':[x*.5 for x in vals],'geometry_scale':[x*.5 for x in vals],
           'audio_clip':[max(-.5,min(.5,x)) for x in vals],'copy_control':[0.]*len(vals)}
    wrappers={'audio_gain':'audio_route','geometry_scale':'ui_route','audio_clip':'clip_route','copy_control':'clear_route'}
    result={}
    for name,expected in cases.items():
        data=(C.c_float*len(vals))(*vals)
        dispatch(callback((name,lib)),data,len(vals),.5)
        err=max(abs(a-b) for a,b in zip(data,expected))
        assert err==0
        fn=getattr(lib,wrappers[name]);fn.argtypes=[C.POINTER(C.c_float),C.c_uint,C.c_float];fn.restype=None
        data=(C.c_float*len(vals))(*vals);fn(data,len(vals),.5)
        wrapper_err=max(abs(a-b) for a,b in zip(data,expected));assert wrapper_err==0
        result[name]={'callback_oracle_max_error':err,'wrapper_oracle_max_error':wrapper_err}
    return {'optimization':opt,'native_sha256':sha(path),'cases':result}


def db(x): return 20*math.log10(max(abs(x),1e-30))
def rms(x): return math.sqrt(math.fsum(v*v for v in x)/len(x))
def tone(fs,hz,amp,n): return [amp*math.sin(2*math.pi*hz*i/fs) for i in range(n)]
def amplitude(x,fs,hz):
    w=2*math.pi*hz/fs
    return 2*math.hypot(math.fsum(v*math.cos(w*i) for i,v in enumerate(x)),math.fsum(v*math.sin(w*i) for i,v in enumerate(x)))/len(x)


def measure_audio(work):
    path=work/'engines.so'
    run('g++','-std=c++17','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror',
        str(ROOT/'tests/fixtures/owned_audio_probe.cpp'),'-o',str(path))
    fn=C.CDLL(str(path)).render_owned
    fn.argtypes=[C.c_int,C.c_double,C.c_double,C.POINTER(C.c_double),C.POINTER(C.c_double),C.c_uint,C.c_uint];fn.restype=C.c_int
    def render(kind,fs,control,l,r,block):
        assert len(l)==len(r) and l
        inp=(C.c_double*(2*len(l)))(*(v for pair in zip(l,r) for v in pair));out=(C.c_double*len(inp))()
        assert fn(kind,fs,control,inp,out,len(l),block)==1
        assert all(math.isfinite(v) for v in out)
        return list(out[::2]),list(out[1::2])
    results=[]
    for fs in (44100,48000,96000):
        n=fs; x=tone(fs,1000,.5,n); r=[v*.37 for v in x]
        row={'sample_rate':fs,'engines':{}}
        for kind,name in enumerate(('presence','leveler','color','color_2x','color_4x')):
            a,b=render(kind,fs,1,x,r,1);c,d=render(kind,fs,1,x,r,257)
            dry_l,dry_r=render(kind,fs,0,x,r,64)
            block_err=max(max(abs(v-w) for v,w in zip(a,c)),max(abs(v-w) for v,w in zip(b,d)))
            latency=40 if kind>=3 else 0
            expected_l=([0.]*latency+x)[:n]; expected_r=([0.]*latency+r)[:n]
            dry_err=max(max(abs(v-w) for v,w in zip(expected_l,dry_l)),max(abs(v-w) for v,w in zip(expected_r,dry_r)))
            pulse=[1.]+[0.]*127; impulse,_=render(kind,fs,0,pulse,pulse,17)
            assert [i for i,v in enumerate(impulse) if v!=0]==[latency] and impulse[latency]==1
            assert block_err==0 and dry_err==0
            row['engines'][name]={'block_partition_max_error':block_err,'dry_max_error':dry_err,
                                  'peak':max(map(abs,a+b)), 'dry_impulse_delay_samples':latency}
        # Presence: compare low/high test tones at a low input level.
        for hz in (100,9000):
            x=tone(fs,hz,.025,fs);a,_=render(0,fs,1,x,x,257)
            row['engines']['presence'][f'{hz}_hz_gain_db']=db(rms(a[-fs//2:])/rms(x[-fs//2:]))
        assert abs(row['engines']['presence']['100_hz_gain_db'])<.1
        assert 2<row['engines']['presence']['9000_hz_gain_db']<3.2
        x=tone(fs,1000,.5,fs);r=[.37*v for v in x];a,b=render(1,fs,1,x,r,257)
        link=max(abs(y-.37*z) for y,z in zip(b,a));assert link<1e-12
        gain=db(rms(a[-fs//2:])/rms(x[-fs//2:]));assert gain<-3
        row['engines']['leveler'].update(steady_gain_db=gain,stereo_link_max_error=link)
        for duration in (.04,1.0):
            loud=int(fs*duration);x=tone(fs,1000,.5,loud)+tone(fs,1000,.02,fs*2)
            a,_=render(1,fs,1,x,x,257);window=fs//100
            recovery=[db(rms(a[loud+t:loud+t+window])/rms(x[loud+t:loud+t+window])) for t in (0,fs//10,fs//2,fs)]
            assert recovery[-1]>recovery[0]
            row['engines']['leveler'][f'recovery_{duration:g}s_db']=recovery
        # Third harmonic of 11 kHz folds below Nyquist at 44.1/48 kHz.
        x=tone(fs,11000,.5,fs*2); target=abs((33000+fs/2)%fs-fs/2)
        for kind,name in ((2,'color'),(3,'color_2x'),(4,'color_4x')):
            a,_=render(kind,fs,1,x,x,257);tail=a[-fs:]
            rel=db(amplitude(tail,fs,target)/amplitude(tail,fs,11000))
            row['engines'][name].update(third_harmonic_observed_hz=target,third_harmonic_relative_db=rel,
                                      third_harmonic_folded=33000>fs/2)
        if 33000>fs/2:
            base=row['engines']['color']['third_harmonic_relative_db']
            assert row['engines']['color_2x']['third_harmonic_relative_db']<base-10
            assert row['engines']['color_4x']['third_harmonic_relative_db']<base-10
        results.append(row)
    return {'native_sha256':sha(path),'rows':results,'limits':'Generated tones only; no vendor audio, runtime or production equivalence. Block partitioning is a harness test, not host integration.'}


def main():
    if not __debug__: raise RuntimeError("Run without optimized Python; assertions are validation gates")
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='skell-owned-') as d:
        work=Path(d)
        report={'schema':1,'static':[static_fixture(work,opt) for opt in ('-O1','-O3')],
                'native':[native_routes(work,opt) for opt in ('-O1','-O3')], 'audio':measure_audio(work)}
        args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Owned static/context and audio checks passed; wrote',args.output)

if __name__=='__main__': main()
