"""Read-only direct caller census: bounded executable scopes, no target execution."""
import struct,hashlib,subprocess,re,bisect,pathlib,json
def audit(path,expected,targets):
 path=pathlib.Path(path)
 if not path.is_file() or path.is_symlink() or not 0<path.stat().st_size<=256*1024*1024:raise ValueError("invalid PE path/size")
 if not isinstance(targets,dict) or not 1<=len(targets)<=64 or any(type(k) is not int or not 0<=k<2**32 or not isinstance(v,str) or not v or len(v)>128 for k,v in targets.items()) or len(set(targets.values()))!=len(targets):raise ValueError("invalid targets")
 data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=expected:raise ValueError("fingerprint mismatch")
 pe=struct.unpack_from('<I',data,60)[0]
 if data[pe:pe+4]!=b'PE\0\0':raise ValueError('not PE')
 n=struct.unpack_from('<H',data,pe+6)[0]; opt=pe+24; size=struct.unpack_from('<H',data,pe+20)[0]
 if not 1<=n<=96 or size<144 or struct.unpack_from('<H',data,opt)[0]!=0x20b or struct.unpack_from('<H',data,pe+4)[0]!=0x8664:raise ValueError('not bounded PE32+ x64')
 base=struct.unpack_from('<Q',data,opt+24)[0];sections=[]
 for i in range(n):
  o=opt+size+40*i; vsize,rva,rawsize,off=struct.unpack_from('<IIII',data,o+8);flags=struct.unpack_from('<I',data,o+36)[0];
  if rawsize and off+rawsize>len(data):raise ValueError("truncated section")
  sections.append((rva,min(vsize,rawsize),off,flags))
 def read(rva,n):
  for a,z,o,_ in sections:
   if a<=rva and rva+n<=a+z:return data[o+rva-a:o+rva-a+n]
  raise ValueError('unmapped')
 exc,sz=struct.unpack_from('<II',data,opt+112+3*8)
 if not exc or not 0<sz<=6000000 or sz%12:raise ValueError('invalid unwind directory')
 ranges=sorted((a,b) for a,b,u in struct.iter_unpack('<III',read(exc,sz)) if a<b);starts=[a for a,b in ranges]; cand={};outside=0
 for a,z,o,flags in sections:
  if not flags&0x20000000:continue
  raw=data[o:o+z]
  for m in re.finditer(b'\xe8',raw):
   i=m.start();site=a+i
   if i+5>z:continue
   dest=site+5+struct.unpack_from('<i',raw,i+1)[0]
   if dest not in targets:continue
   j=bisect.bisect_right(starts,site)-1
   if j<0 or site+5>ranges[j][1] or ranges[j][1]-ranges[j][0]>32768:outside+=1;continue
   cand.setdefault(ranges[j],[]).append((site,dest))
 if len(cand)>=256:raise ValueError("scope limit exceeded")
 results={name:{'byte_candidates':0,'confirmed_calls':0,'caller_scopes':0} for name in targets.values()}; scope_rows=[]
 for (a,b),calls in cand.items():
  maps=[]
  for exe in ['objdump','llvm-objdump']:
   text=subprocess.check_output([exe,'-d',f'--start-address={base+a:#x}',f'--stop-address={base+b:#x}',str(path)],text=True,timeout=10)
   pat=r'^\s*([0-9a-fA-F]+):\s+e8(?:\s+[0-9a-fA-F]{2}){4}\s+callq?\s+(?:0x)?([0-9a-fA-F]+)\b'
   maps.append({(int(x,16)-base,int(y,16)-base) for x,y in re.findall(pat,text,re.M)})
  ok=set(calls)&maps[0]&maps[1];names=set()
  for site,dest in calls:results[targets[dest]]['byte_candidates']+=1
  for site,dest in ok:results[targets[dest]]['confirmed_calls']+=1;names.add(targets[dest])
  for name in names:results[name]['caller_scopes']+=1
  if ok:scope_rows.append({'scope_hash':hashlib.sha256(read(a,b-a)).hexdigest(),'confirmed_target_labels':sorted(names),'count':len(ok)})
 if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError("source changed")
 return {'source_sha256':expected,'targets':results,'out_of_scope_candidates':outside,'scopes':scope_rows,'limits':'Direct E8 only, executable file sections, complete bounded unwind scopes, GNU/LLVM consensus; indirect, tail calls, leaf and runtime dispatch unresolved.'}

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary');p.add_argument('sha256');p.add_argument('targets',nargs='+',help='RVA:label (hex RVA)');a=p.parse_args()
 pairs=[x.split(':',1) for x in a.targets];targets={int(k,16):v for k,v in pairs}
 if len(targets)!=len(pairs):raise ValueError('duplicate targets')
 print(json.dumps(audit(a.binary,a.sha256,targets),indent=2,allow_nan=False))
