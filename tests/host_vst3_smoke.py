"""Windows only: load the owned CI-built VST3 via the public host adapter."""
import argparse
import json
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf
from skell_vst_decompiler.host_capture import bundle_hash,run_matrix
from skell_vst_decompiler.reference_lab import digest


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
                plan.append({'id':f'g{int(gain*100)}_{n}','case':'probe','spec':{'backend':'installed_vst3','authorization':'installed_and_licensed','purpose':'owned_fixture','path':str(plugin),'sha256':sha,'version':'1.0.0','parameters':{'gain':gain},'block_size':n,'target_stage':'output'}})
        out=Path(tmp)/'capture';rows=run_matrix(root,plan,out,authorized=True,timeout=90)
        assert all(r['status']=='captured' for r in rows),rows
        summary=[]
        for row,job in zip(rows,plan):
            y,_=sf.read(out/row['id']/'render.wav',always_2d=True);gain=job['spec']['parameters']['gain'];meta=row['metadata']
            err=float(np.max(abs(y-x*gain)));assert err<1e-7 and meta['evidence']=='EXEC: fixture' and abs(meta['parameter_readback']['gain']-gain)<1e-5
            summary.append({'id':row['id'],'max_error':err,'latency_reported':meta['reported_latency_samples']})
        print('SKELL_OWNED_VST3_RESULT '+json.dumps({'bundle_sha256':sha,'cases':summary},sort_keys=True))


if __name__=='__main__':main()
