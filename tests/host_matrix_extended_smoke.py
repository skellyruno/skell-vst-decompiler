"""Seeded parameter/rate/block controls using independent built-in effects only."""
import json
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf
from skell_vst_decompiler.host_capture import run_matrix
from skell_vst_decompiler.reference_lab import digest
from skell_vst_decompiler.divergence import first_difference


def main():
    summaries=[]
    with tempfile.TemporaryDirectory() as d:
        for fs in (44100,48000,96000):
            root=Path(d)/str(fs);root.mkdir()
            rng=np.random.default_rng(291+fs);n=fs//4
            x=rng.uniform(-.4,.4,(n,2)).astype(np.float32)
            # Explicit low/high-level history and a zero-input ending.
            x[:n//4]*=.1;x[-n//8:]=0
            src=root/'probe.wav';sf.write(src,x,fs,subtype='FLOAT')
            (root/'manifest.json').write_text(json.dumps({'schema':1,'sample_rate':fs,'cases':[{'id':'probe','family':'dynamics','file':src.name,'sha256':digest(src),'frames':n,'windows':[]}]}))
            gain=float(rng.uniform(-18,6));threshold=float(rng.uniform(-32,-18));ratio=float(rng.uniform(2,6));attack=float(rng.uniform(1,25));release=float(rng.uniform(30,200))
            cases={'Gain':{'gain_db':gain},'Compressor':{'threshold_db':threshold,'ratio':ratio,'attack_ms':attack,'release_ms':release}}
            plan=[{'id':f'{name}_{block}','case':'probe','spec':{'backend':'fixture','name':name,'parameters':params,'block_size':block,'target_stage':'output'}} for name,params in cases.items() for block in (64,1024)]
            out=root/'captures';rows=run_matrix(root,plan,out)
            assert all(r['status']=='captured' for r in rows),rows
            for name in cases:
                a,b=(sf.read(out/f'{name}_{block}'/'render.wav',always_2d=True)[0] for block in (64,1024))
                cmp=first_difference(a,b,fs,atol=0,rtol=0)
                assert cmp['mismatched_samples']==0,cmp
                oracle=float(np.max(abs(a-x*10**(gain/20)))) if name=='Gain' else None
                if oracle is not None:assert oracle<2e-7
                summaries.append({'sample_rate':fs,'effect':name,'parameters':cases[name],'frames':n,'compared_samples':n*2,'max_block_difference':cmp['max_absolute_error'],'gain_oracle_max_error':oracle})
    print('SKELL_EXTENDED_HOST_RESULT '+json.dumps({'cases':summaries,'renders':2*len(summaries)},sort_keys=True))


if __name__=='__main__':main()
