"""Windows only: load the owned CI-built VST3 via the public host adapter."""
import argparse
import json
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf
from skell_vst_decompiler.host_capture import bundle_hash,run_matrix
from skell_vst_decompiler.reference_lab import digest
from skell_vst_decompiler.impulse_calibration import inspect_impulse


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plugin');args=p.parse_args();plugin=Path(args.plugin).resolve()
    sha=bundle_hash(plugin)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/'probes';root.mkdir();fs=48000;t=np.arange(4800)/fs
        x=np.column_stack((.25*np.sin(2*np.pi*997*t),.2*np.cos(2*np.pi*701*t))).astype(np.float32)
        source=root/'probe.wav';sf.write(source,x,fs,subtype='FLOAT')
        (root/'manifest.json').write_text(json.dumps({'schema':1,'sample_rate':fs,'cases':[{'id':'probe','family':'linear','file':source.name,'sha256':digest(source),'frames':len(x),'windows':[]}]}))
        plan=[]
        for n in (64,1024):
            for gain in (.25,.75):
                plan.append({'id':f'g{int(gain*100)}_{n}','case':'probe','spec':{'backend':'installed_vst3','authorization':'installed_and_licensed','purpose':'owned_fixture','path':str(plugin),'sha256':sha,'version':'1.0.0','parameters':{'gain':gain},'expected_normalized':{'gain':gain},'block_size':n,'target_stage':'output'}})
        out=Path(tmp)/'capture';rows=run_matrix(root,plan,out,authorized=True,timeout=90)
        assert all(r['status']=='captured' for r in rows),rows
        summary=[]
        for row,job in zip(rows,plan):
            y,_=sf.read(out/row['id']/'render.wav',always_2d=True);gain=job['spec']['parameters']['gain'];meta=row['metadata']
            err=float(np.max(abs(y-x*gain)));assert err<1e-7 and meta['evidence']=='EXEC: fixture' and abs(meta['parameter_readback']['gain']-gain)<1e-5
            summary.append({'id':row['id'],'max_error':err,'latency_reported':meta['reported_latency_samples']})
        # Additional independent impulse case, with exact creative delay and reported zero latency.
        impulse=np.zeros((4813,2),np.float32);impulse[7,1]=.5
        f=root/'impulse.wav';sf.write(f,impulse,fs,subtype='FLOAT')
        m=json.loads((root/'manifest.json').read_text());m['cases'].append({'id':'impulse','family':'linear','file':f.name,'sha256':digest(f),'frames':len(impulse),'windows':[]});(root/'manifest.json').write_text(json.dumps(m))
        delay_plan=[]
        for n in (64,1024):
            spec=dict(plan[0]['spec'],parameters={'gain':.5,'creative_delay':True},expected_normalized={'gain':.5,'creative_delay':1.},block_size=n)
            delay_plan.append({'id':f'delay_{n}','case':'impulse','spec':spec})
        d_out=Path(tmp)/'delay';d_rows=run_matrix(root,delay_plan,d_out,authorized=True,timeout=90)
        assert all(r['status']=='captured' for r in d_rows),d_rows
        for row in d_rows:
            y,_=sf.read(d_out/row['id']/'render.wav',always_2d=True);meta=row['metadata']
            expected=np.zeros_like(impulse);expected[137:]=impulse[:-137]*.5
            err=float(np.max(abs(y-expected)));assert err==0 and meta['reported_latency_samples']==0
            timing=inspect_impulse(impulse,y,fs,reported_latency=meta['reported_latency_samples'])
            assert timing['outputs'][1]['first_arrival_samples']==137 and timing['outputs'][0]['first_arrival_samples'] is None
            summary.append({'id':row['id'],'max_error':err,'latency_reported':0,'creative_delay_samples':137})
        print('SKELL_OWNED_VST3_RESULT '+json.dumps({'bundle_sha256':sha,'cases':summary},sort_keys=True))


if __name__=='__main__':main()
