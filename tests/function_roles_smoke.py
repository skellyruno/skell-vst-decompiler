"""Compiled role holdout: identical evidence rules, no label/name features."""
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.disasm import disassemble
from skell_vst_decompiler.function_roles import role_evidence, FP

LABELS={'gain':True,'filter':True,'curve':True,'byte_copy':False,'setup':False,
        'scalar_math':False,'geometry':False,'unknown':None}


def export_scopes(pe):
    opt=struct.unpack_from('<I',pe.data,60)[0]+24
    rva,size=struct.unpack_from('<II',pe.data,opt+112)
    _,_,_,_,_,_,nf,nn,funcs,names,ords=struct.unpack('<IIHHIIIIIII',pe.at_rva(rva,40))
    if nf!=len(LABELS) or nn!=nf:raise ValueError('Unexpected owned fixture export count')
    entries={}
    for i in range(nn):
        name=pe.cstring_rva(pe.u32(names+4*i));ordinal=struct.unpack('<H',pe.at_rva(ords+2*i,2))[0]
        if ordinal>=nf:raise ValueError('Invalid ordinal')
        entries[name]=pe.u32(funcs+4*ordinal)
    if set(entries)!=set(LABELS):raise ValueError('Unexpected owned fixture names')
    end=pe.section('.text').rva+pe.section('.text').virtual_size
    return [(k,start,min([v for v in entries.values() if v>start]+[end])) for k,start in entries.items()]


def main():
    source=Path(__file__).resolve().parents[1]/'experiments/ground_truth/RoleFixture.cpp'
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        for opt in ('-O1','-O3'):
            obj=root/'owned.obj';dll=root/'owned.dll'
            subprocess.run(['clang++','--target=x86_64-pc-windows-msvc','-ffreestanding','-fno-exceptions','-fno-rtti','-fno-stack-protector',opt,'-c',str(source),'-o',str(obj)],check=True,timeout=30)
            subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/out:'+str(dll),str(obj)],check=True,timeout=30)
            pe=PE(dll)
            for name,start,end in export_scopes(pe):
                a=disassemble(pe,start,end-start,'objdump');b=disassemble(pe,start,end-start,'llvm-objdump')
                x,y=role_evidence(a),role_evidence(b)
                # Decoder counts may differ in padding; do not hide role disagreements.
                role=x['role'] if x['role']==y['role'] else 'UNRESOLVED'
                old=sum(bool(FP.fullmatch(i.mnemonic)) for i in a)>=4 and sum('[' in i.operands and ('xmm' in i.operands or 'ymm' in i.operands) for i in a)>=2
                rows.append(dict(name=name,opt=opt,truth=LABELS[name],old=old,role=role,decoder_agreement=x['role']==y['role'],binary_sha256=pe.sha256))
    assert len(rows)==16 and all(r['decoder_agreement'] for r in rows),rows
    assert all(r['role']=='UNRESOLVED' for r in rows if r['name']=='unknown'),rows
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
