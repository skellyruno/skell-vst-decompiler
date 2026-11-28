import tempfile,json
from pathlib import Path
import numpy as np,pedalboard as pb,soundfile as sf
from benchmarks.topology_capture_probes import generate
from skell_vst_decompiler.capture_intake import sources,seal,analyze
rows=[]
for fs in (44100,48000,96000):
    with tempfile.TemporaryDirectory() as d:
        r=Path(d);p=r/'probes';w=r/'wet';w.mkdir();generate(p,fs,2);_,x,_=sources(p)
        for k,v in x.items():
            y=pb.Reverb(room_size=.5,wet_level=1,dry_level=0).process(np.ascontiguousarray(v.T,dtype=np.float32),fs,buffer_size=128,reset=True).T
            sf.write(w/(k+'.wav'),y,fs,subtype='FLOAT')
        sf.write(w/'bypass.wav',x['base'],fs,subtype='FLOAT')
        decl=r/'decl.json';decl.write_text(json.dumps(dict(plugin='Independent Reverb',version=pb.__version__,host='Pedalboard built-in fixture',settings='room_size=.5 wet_level=1 dry_level=0',target_stage='output',authorized=True,isolated=True,fresh_reset=True,no_normalization=True,same_settings=True,alignment='owner_verified_active_timeline',alignment_note='Known fixture sample index; no shift applied',reported_latency_samples=0)))
        session=r/'session.json';seal(p,w,decl,session);a=analyze(p,w,session);rows.append(a);print(fs,a['status'],max(a['peak_by_case'].values()),a.get('candidates'))
Path('quiet_reverb_results.json').write_text(json.dumps(dict(scope='independent reverb fixture at half-level original probes',renders=33,results=rows),indent=2,allow_nan=False)+'\n')
