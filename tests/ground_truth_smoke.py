"""Build only our source, blind static family ranking, independently run owned native kernels."""
import ctypes as ct
import hashlib
import json
from pathlib import Path
import shutil
import re
import struct
import subprocess
import tempfile
import numpy as np
from skell_vst_decompiler.ground_truth import fingerprint,rank,evaluate
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.disasm import disassemble
from skell_vst_decompiler.analyzer_worker import stimuli,describe,behavior_candidate,state_difference

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'experiments/ground_truth/Kernel.cpp'
LABELS=['gain','clip','filter','delay','envelope',None]


def build(root,family,variant,opt,ident):
    common=[f'-DFAMILY={family}',f'-DVARIANT={variant}',opt,str(SOURCE)]
    obj=root/(ident+'.obj');dll=root/(ident+'.dll')
    subprocess.run(['clang++','--target=x86_64-pc-windows-msvc','-ffreestanding','-fno-exceptions','-fno-rtti','-fno-stack-protector',*common,'-c','-o',str(obj)],check=True,timeout=30)
    subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/out:'+str(dll),str(obj)],check=True,timeout=30)
    a=fingerprint(dll);b=fingerprint(dll,'llvm-objdump')
    # Each decoder's independently extracted features must agree for the fixture.
    if a!=b:raise AssertionError((ident,a,b))
    # Known fixture ABI gives exact source entry points independently of ranking.
    pe=PE(dll);end=pe.section('.text').rva+pe.section('.text').virtual_size
    opt=struct.unpack_from('<I',pe.data,60)[0]+24
    rva,size=struct.unpack_from('<II',pe.data,opt+112)
    _,_,_,_,_,_,nf,nn,funcs,names_table,ords=struct.unpack('<IIHHIIIIIII',pe.at_rva(rva,40))
    if nf!=2 or nn!=2:raise ValueError('Unexpected fixture export count')
    names={}
    for i in range(nn):
        name=pe.cstring_rva(pe.u32(names_table+4*i));ordinal=struct.unpack('<H',pe.at_rva(ords+2*i,2))[0]
        if ordinal>=nf:raise ValueError('Invalid fixture ordinal')
        names[name]=pe.u32(funcs+4*ordinal)
    if set(names)!={'process','set_control'}:raise ValueError('Fixture export identity missing')
    def endpoints(tool):
        setter=[];reads=[]
        for name,start in names.items():
            stop=min([x for x in names.values() if x>start]+[end])
            for ins in disassemble(pe,start,stop-start,tool):
                op=ins.operands.lower().replace(' ','')
                if name=='set_control' and ins.mnemonic=='movss' and op=='dwordptr[rcx],xmm1':setter.append(hex(ins.address-pe.image_base))
                if name=='process' and ins.mnemonic in ('movss','mulss','addss','subss','divss') and re.fullmatch(r'xmm\d+,dwordptr\[rdx\]',op):reads.append(hex(ins.address-pe.image_base))
        return {'setter_sites':setter,'process_read_sites':reads}
    e1,e2=endpoints('objdump'),endpoints('llvm-objdump')
    if e1!=e2:raise AssertionError((ident,e1,e2))
    a['owned_source_entry_rvas']={k:hex(v) for k,v in names.items()}
    a['direct_abi_offset_zero_evidence']=e1
    return a


def native(root,family,variant,ident):
    so=root/(ident+'.so')
    subprocess.run(['g++','-std=c++17','-shared','-fPIC','-O3','-Wall','-Wextra','-Werror',f'-DFAMILY={family}',f'-DVARIANT={variant}',str(SOURCE),'-o',str(so)],check=True,timeout=30)
    lib=ct.CDLL(str(so));ptr=ct.POINTER(ct.c_float)
    lib.set_control.argtypes=[ptr,ct.c_float];lib.set_control.restype=None
    lib.process.argtypes=[ct.c_float,ptr];lib.process.restype=ct.c_float
    def state(p):
        s=(ct.c_float*16)();lib.set_control(s,p);return s
    a,b,c=bytes(state(.25)),bytes(state(.25)),bytes(state(.75))
    diff=state_difference(a,b,c)
    assert diff['stable_changed_bytes']>0 and all(lo>=0 and hi<=4 for lo,hi in diff['spans']) and diff['unstable_baseline_bytes']==0
    probes=stimuli();metrics=[]
    for p in (.25,.75):
        out={}
        for k,x in probes.items():
            s=state(p);out[k]=np.array([lib.process(float(v),s) for v in x],dtype=np.float32)
        metrics.append(describe(probes,out))
    pred=behavior_candidate(metrics[0]);label=['gain','level_dependent_no_observed_memory','filter','delay','level_dependent_memory','unresolved'][family]
    assert pred==label,(family,pred,metrics[0])
    # Validate observable parameter change, not just bytes changing.
    assert (metrics[0]!=metrics[1])==(family!=5),(family,metrics)
    return {'family':LABELS[family] or 'unknown','behavior':pred,'state_spans':diff['spans'],'parameter_changes_audio':metrics[0]!=metrics[1],
            'baseline':metrics[0],'changed':metrics[1],'native_sha256':hashlib.sha256(so.read_bytes()).hexdigest()}


def main():
    for tool in ('clang++','lld-link','objdump','llvm-objdump','g++'):
        if not shutil.which(tool):raise RuntimeError('Missing '+tool)
    with tempfile.TemporaryDirectory(prefix='skell-ground-') as tmp:
        root=Path(tmp);train=[];train_rows=[];blind={};truth={};native_rows=[]
        for family,label in enumerate(LABELS[:-1]):
            obs=build(root,family,0,'-O2',f't{family}');train.append((label,obs['features']));train_rows.append({'family':label,**obs})
        # All holdout compilations complete before predictions. Labels never enter features.
        for j,opt in enumerate(('-O1','-O3','-O0')):
            for i,label in enumerate(LABELS):
                ident=f'h{j}_{i}';blind[ident]=build(root,i,1,opt,ident);truth[ident]=label
        ranked={k:rank(v['features'],train) for k,v in blind.items()};pred={k:v['candidate'] for k,v in ranked.items()}
        for i in range(len(LABELS)):native_rows.append(native(root,i,1,f'n{i}'))
        report={'schema_version':1,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'training':train_rows,'holdout':[{'id':k,'expected':truth[k],**blind[k],**ranked[k]} for k in blind],
                'static_metrics':evaluate(pred,truth),
                'direct_parameter_join_count':sum(bool(v['direct_abi_offset_zero_evidence']['setter_sites'] and v['direct_abi_offset_zero_evidence']['process_read_sites']) for v in blind.values()),'behavioral_owned_native':native_rows,
                'limitations':'Small freestanding PE fixtures, same compiler family and partly shared source. Separate native Linux build for audio; not Windows VST3 execution or arbitrary-plugin generalization.'}
        print(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':main()
