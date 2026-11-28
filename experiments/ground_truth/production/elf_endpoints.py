"""Bounded static source-known ELF endpoint verification for Skelly Master."""
import hashlib,json,re,struct,subprocess,sys
from pathlib import Path
EXPECTED='82edf9789d1f2632f6f707ee9739f9d1e54f9e5e0781d829a9016ddc513876c3'
START,END=0x12f820,0x133ed9
LOOKUP,SET,PROCESS=0x168370,0x139dd0,0x13a610
NAMES=('input','drive','glue','lows','highs','width','spatialWidth','clipper')

def read_elf(path):
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=EXPECTED or data[:6]!=b'\x7fELF\x02\x01':raise ValueError('Wrong exact source')
    phoff=struct.unpack_from('<Q',data,32)[0];ents,n=struct.unpack_from('<HH',data,54)
    if ents!=56 or n>128:raise ValueError('Invalid ELF program header')
    loads=[]
    for i in range(n):
        kind,flags,off,va,_,size,_,_=struct.unpack_from('<II6Q',data,phoff+i*ents)
        if kind==1:
            if off+size>len(data):raise ValueError('Truncated ELF')
            loads.append((va,off,size,flags))
    def read(va,size,execute=False):
        matches=[(v,o) for v,o,n,f in loads if v<=va and va-v+size<=n and (not execute or f&1)]
        if len(matches)!=1:raise ValueError('Unbacked or ambiguous range')
        v,o=matches[0];return data[o+va-v:o+va-v+size]
    return read

def extract(path,tool):
    if tool not in ('objdump','llvm-objdump'):raise ValueError('Unknown decoder')
    read=read_elf(path)
    args=[tool,'-d',f'--start-address={START:#x}',f'--stop-address={END:#x}']+(['-w','-M','intel'] if tool=='objdump' else ['--x86-asm-syntax=intel'])+[str(path)]
    out=subprocess.check_output(args,text=True,timeout=30)
    ins=[]
    for line in out.splitlines():
        m=re.match(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)(\S+)(?:\s+(.*))?$',line)
        if m:
            va=int(m[1],16);raw=bytes.fromhex(m[2]);op=m[3];operand=(m[4] or '').split('#')[0].lower().replace(' ','')
            if read(va,len(raw),True)!=raw:raise ValueError('Instruction byte mismatch')
            ins.append((va,raw,op,operand))
    rows=[];calls={SET:[],PROCESS:[]}
    pending=None;active=None
    for va,raw,op,arg in ins:
        if op=='lea' and len(raw)==7 and raw[:3]==b'\x48\x8d\x35':
            target=va+7+int.from_bytes(raw[3:],'little',signed=True)
            name=next((n for n in NAMES if read(target,len(n)+1)==n.encode()+b'\0'),None)
            if name:pending=(name,va,target)
        if op=='call' and len(raw)==5 and raw[0]==0xe8:
            target=va+5+int.from_bytes(raw[1:],'little',signed=True)
            if target in calls:calls[target].append(va)
            if target==LOOKUP:
                active=(*pending,va) if pending and va-pending[1]<180 else None;pending=None
        if active and op=='movsd' and re.fullmatch(r'qwordptr\[rsp\+0x[0-9a-f]+\],xmm0',arg):
            name,ref,string_va,lookup=active
            if va-lookup<80:
                offset=int(re.search(r'rsp\+0x([0-9a-f]+)',arg)[1],16)
                rows.append({'source_id':name,'string_va':hex(string_va),'string_ref':hex(ref),'lookup_call':hex(lookup),'store_va':hex(va),'stack_offset':hex(offset),'parameter_struct_offset':hex(offset-0x160)})
            active=None
    # The source-known first eight requested fields occur once before setParameters.
    rows=[r for r in rows if int(r['store_va'],16)<calls[SET][0]]
    if len(rows)!=len(NAMES) or {r['source_id'] for r in rows}!=set(NAMES) or len(calls[SET])!=1 or len(calls[PROCESS])!=2:raise ValueError('Incomplete or ambiguous endpoint set')
    # Verify the call argument is the struct base, then the callee's member reads.
    if read(0x12f923,8,True)!=bytes.fromhex('488dac2460010000') or read(0x12fe27,3,True)!=bytes.fromhex('4889ee'):
        raise ValueError('Struct call argument mismatch')
    args=[tool,'-d','--start-address=0x139dd0','--stop-address=0x13a60c']+(['-w','-M','intel'] if tool=='objdump' else ['--x86-asm-syntax=intel'])+[str(path)]
    setter=subprocess.check_output(args,text=True,timeout=30)
    if read(0x139dd9,3,True)!=bytes.fromhex('4889f5'):raise ValueError('Callee argument base mismatch')
    for row in rows:
        offset=int(row['parameter_struct_offset'],16);sites=[]
        for line in setter.splitlines():
            m=re.match(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)movsd\s+(.*)$',line)
            if not m:continue
            va=int(m[1],16);raw=bytes.fromhex(m[2]);op=m[3].lower().replace(' ','')
            match=re.fullmatch(r'xmm\d+,qwordptr\[rbp(?:\+0x([0-9a-f]+))?\]',op)
            if match and int(match[1] or '0',16)==offset:
                if read(va,len(raw),True)!=raw:raise ValueError('Callee instruction mismatch')
                sites.append(hex(va))
        if not sites:raise ValueError('No corresponding callee member read')
        row['setter_member_reads']=sites
    return {'module_sha256':EXPECTED,'process_block':[hex(START),hex(END)],'lookup_target':hex(LOOKUP),'set_parameters_target':hex(SET),'set_parameters_calls':[hex(x) for x in calls[SET]],'process_frame_target':hex(PROCESS),'process_frame_calls':[hex(x) for x in calls[PROCESS]],'rows':rows}
if __name__=='__main__':
    a=extract(sys.argv[1],'objdump');b=extract(sys.argv[1],'llvm-objdump')
    if a!=b:raise ValueError('Decoder disagreement')
    print(json.dumps(a,indent=2))
