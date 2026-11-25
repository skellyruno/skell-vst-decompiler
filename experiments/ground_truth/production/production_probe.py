"""Read-only semantic state and audio probes for our verified Skelly Master build."""
import argparse,hashlib,json,math,struct,sys,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
ALPHABET='.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+'
MAX=4*1024*1024
EXPECTED='82edf9789d1f2632f6f707ee9739f9d1e54f9e5e0781d829a9016ddc513876c3'
def sha(data):return hashlib.sha256(data).hexdigest()
def decode_memoryblock(value):
    size,sep,encoded=value.partition('.')
    if not sep or not size.isascii() or not size.isdecimal() or len(size)>8:raise ValueError('Invalid memoryblock size')
    n=int(size)
    if not 0<n<=MAX or len(encoded)!=(n*8+5)//6:raise ValueError('Invalid memoryblock length')
    out=bytearray();acc=bits=0
    for ch in encoded:
        v=ALPHABET.find(ch)
        if v<0:raise ValueError('Invalid memoryblock alphabet')
        acc|=v<<bits;bits+=6
        if bits>=8:out.append(acc&255);acc>>=8;bits-=8
    if len(out)!=n or acc:raise ValueError('Noncanonical memoryblock')
    return bytes(out)
def parse_xml_state(raw, *, allow_opaque_tail=False):
    if len(raw)<8 or len(raw)>MAX or raw[:4]!=b'VC2!':raise ValueError('Invalid JUCE XML state')
    n=struct.unpack_from('<I',raw,4)[0]
    if not 0<n<=len(raw)-8 or (not allow_opaque_tail and any(raw[8+n:])):raise ValueError('Invalid XML length/padding')
    xml=raw[8:8+n]
    if b'<!' in xml:raise ValueError('Unsupported XML declaration')
    return ET.fromstring(xml)
def state_fields(raw):
    wrapper=parse_xml_state(raw)
    if wrapper.tag!='VST3PluginState' or len(wrapper.findall('IComponent'))!=1:raise ValueError('Unexpected host state')
    component_bytes=decode_memoryblock(wrapper.find('IComponent').text or '')
    component=parse_xml_state(component_bytes,allow_opaque_tail=True)
    opaque_tail=component_bytes[8+struct.unpack_from('<I',component_bytes,4)[0]:]
    if component.tag!='SKELLY_MASTER_PARAMETERS':raise ValueError('Unexpected owned component state')
    result={}
    for e in component.findall('PARAM'):
        key=e.attrib['id'];value=float(e.attrib['value'])
        if key in result or not math.isfinite(value):raise ValueError('Invalid parameter field')
        result[key]=value
    return result,dict(component.attrib,opaque_tail_sha256=sha(opaque_tail))
BASE={'input_db':.5,'drive':.10,'glue':0.,'dynamics':0.,'lows_db':.5,'highs_db':.5,'sauce':0.,'transients':0.,'output_trim_db':.6,'ceiling_adjust_step':.5,'clip':0.,'bypass':0.,'deuce_match':0.,'width':.625,'spatial_width':0.}
POINTS={'input_db':('input',.75),'drive':('drive',.60),'glue':('glue',.65),'lows_db':('lows',.75),'highs_db':('highs',.75),'width':('width',.25),'spatial_width':('spatialWidth',.65),'clip':('clipper',.55)}
def probe_data(fs):
    t=np.arange(fs)/fs
    return {'low':np.tile(.18*np.sin(2*np.pi*100*t),(2,1)).astype('float32'),'high':np.tile(.18*np.sin(2*np.pi*7000*t),(2,1)).astype('float32'),'level':np.tile(np.where((t>.25)&(t<.65),.80,.08)*np.sin(2*np.pi*1000*t),(2,1)).astype('float32'),'stereo':np.array([.23*np.sin(2*np.pi*701*t)+.15*np.sin(2*np.pi*1800*t),.23*np.sin(2*np.pi*701*t)-.15*np.sin(2*np.pi*1800*t)],dtype='float32')}
def capture(path,key,value):
    import pedalboard as pb
    if pb.__version__!='0.9.23':raise ValueError('Host version mismatch')
    p=Path(path);mod=p/'Contents/x86_64-linux/Skelly Master.so'
    if sha(mod.read_bytes())!=EXPECTED:raise ValueError('Wrong owned binary')
    fx=pb.load_plugin(str(p),initialization_timeout=10)
    if fx.name!='Skelly Master' or fx.version!='1.0.0' or not fx.is_effect:raise ValueError('Wrong plugin')
    settings=dict(BASE)
    if key!='baseline':settings[key]=value
    if set(settings)!=set(fx.parameters):raise ValueError('Parameter inventory mismatch')
    for k,v in settings.items():fx.parameters[k].raw_value=v
    read={k:float(p.raw_value) for k,p in fx.parameters.items()}
    if any(abs(read[k]-v)>1e-5 for k,v in settings.items()):raise ValueError('Parameter mismatch')
    raw=bytes(fx.raw_state);fields,props=state_fields(raw)
    captures={};fs=48000
    for n,x in probe_data(fs).items():
        y=fx.process(x,fs,buffer_size=256,reset=True)
        if y.shape!=x.shape or not np.isfinite(y).all():raise ValueError('Invalid audio')
        s=y[:,fs//4:3*fs//4].astype('float64');mid=(s[0]+s[1])*.5;side=(s[0]-s[1])*.5
        captures[n]={'hash':sha(y.tobytes()),'rms':float(np.sqrt(np.mean(s*s))),'side_rms':float(np.sqrt(np.mean(side*side))),'mid_rms':float(np.sqrt(np.mean(mid*mid))),'peak':float(np.max(abs(y)))}
    if sha(mod.read_bytes())!=EXPECTED or read!={k:float(p.raw_value) for k,p in fx.parameters.items()}:raise ValueError('Plugin or control changed')
    return {'key':key,'state_fields':fields,'state_properties':props,'readback':read,'state_sha256':sha(raw),'probes':captures,'latency_after_process':int(fx.reported_latency_samples)}
def pair(path,k,v):
    rows=[json.loads(subprocess.check_output([sys.executable,__file__,path,'--child',k,str(v)],timeout=40,text=True)) for _ in range(2)]
    if rows[0]!=rows[1]:raise ValueError('Unstable replicate: '+k)
    return rows[0]
def observation(base,changed,k):
    source_id,v=POINTS[k]
    delta={s:[base['state_fields'][s],changed['state_fields'][s]] for s in base['state_fields'] if base['state_fields'][s]!=changed['state_fields'][s]}
    if set(delta)!={source_id}:raise ValueError(f'Unexpected semantic state delta: {k} {delta}')
    if base['state_properties']!=changed['state_properties']:raise ValueError('Unexpected nonparameter state delta')
    return {'host_key':k,'source_id':source_id,'normalized':[base['readback'][k],changed['readback'][k]],'state_delta':delta,'audio_changed':any(base['probes'][n]['hash']!=changed['probes'][n]['hash'] for n in base['probes']),'repeat_exact':True,'probe_metrics':{n:{m:changed['probes'][n][m] for m in ('rms','side_rms','mid_rms','peak')} for n in changed['probes']}}
def main():
    p=argparse.ArgumentParser();p.add_argument('bundle');p.add_argument('--child',nargs=2);p.add_argument('--point',choices=['baseline',*POINTS]);a=p.parse_args()
    if a.child:print(json.dumps(capture(a.bundle,a.child[0],float(a.child[1])),allow_nan=False));return
    if a.point:print(json.dumps(pair(a.bundle,a.point,POINTS.get(a.point,('',0))[1]),allow_nan=False));return
    base=pair(a.bundle,'baseline',0);observations=[observation(base,pair(a.bundle,k,v),k) for k,(_,v) in POINTS.items()]
    print(json.dumps({'module_sha256':EXPECTED,'sample_rate':48000,'block_size':256,'host':'Pedalboard 0.9.23 Linux','baseline_metrics':base['probes'],'baseline_latency_after_process':base['latency_after_process'],'baseline_normalized':base['readback'],'observations':observations,'fresh_processes':2*(1+len(observations))},indent=2,allow_nan=False))
if __name__=='__main__':main()
