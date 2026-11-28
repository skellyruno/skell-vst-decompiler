"""Exercise manual capture intake on actual independent built-in effects, not commercial targets."""
import json,tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import pedalboard as pb
from benchmarks.topology_capture_probes import generate
from skell_vst_decompiler.capture_intake import seal,analyze,sources


def main():
    rows=[];renders=0
    configs=[('Gain',{'gain_db':-3}),('PeakFilter',{'cutoff_frequency_hz':1000,'gain_db':3}),('Clipping',{'threshold_db':-12}),('Compressor',{'threshold_db':-24,'ratio':4,'attack_ms':5,'release_ms':150}),('Delay',{'delay_seconds':.07,'feedback':.2,'mix':1}),('Chorus',{'rate_hz':.73,'depth':.6,'mix':1}),('Reverb',{'room_size':.5,'wet_level':1,'dry_level':0})]
    for fs in (44100,48000,96000):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);probes=root/'probes';generate(probes,fs);_,x,_=sources(probes)
            for name,kw in configs:
                wet=root/name;wet.mkdir();decl=wet/'declaration.json';session=wet/'session.json'
                for key,v in x.items():
                    y=getattr(pb,name)(**kw).process(np.ascontiguousarray(v.T,dtype=np.float32),fs,buffer_size=128,reset=True).T;renders+=1
                    sf.write(wet/(key+'.wav'),y,fs,subtype='FLOAT')
                sf.write(wet/'bypass.wav',x['base'],fs,subtype='FLOAT')
                decl.write_text(json.dumps(dict(plugin='Independent '+name,version=pb.__version__,host='Pedalboard built-in fixture',settings=json.dumps(kw,sort_keys=True),target_stage='output',authorized=True,isolated=True,fresh_reset=True,no_normalization=True,same_settings=True,alignment='owner_verified_active_timeline',alignment_note='Known fixture sample index; no shift applied',reported_latency_samples=0)))
                seal(probes,wet,decl,session);r=analyze(probes,wet,session);rows.append(r);print(fs,name,r['status'],r.get('candidates'),flush=True)
    Path('capture_intake_results.json').write_text(json.dumps(dict(scope='independent fixtures; metadata synthetic, not commercial captures',renders=renders,results=rows),indent=2,allow_nan=False)+'\n')
    print('renders',renders)
if __name__=='__main__':main()
