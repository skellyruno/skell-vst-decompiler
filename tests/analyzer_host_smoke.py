"""Windows CI: only build-owned VST3s, never arbitrary vendor binaries."""
import argparse
import json
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf
from skell_vst_decompiler.analyzer_worker import run_sweep, run_parameter_map
from skell_vst_decompiler.host_capture import bundle_hash,run_matrix
from skell_vst_decompiler.reference_lab import digest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('fixture');p.add_argument('analyzer');a=p.parse_args()
    fixture=Path(a.fixture).resolve();analyzer=Path(a.analyzer).resolve()
    spec={'authorization':'installed_and_licensed','purpose':'owned_fixture','path':str(fixture),'sha256':bundle_hash(fixture),'version':'1.0.0'}
    result=run_sweep(spec,'gain',[.25,.75])
    assert all(r['status']=='captured' for r in result['rows']),result
    assert result['repeat_metrics_stable'],result
    row=result['rows'][-1]
    assert abs(row['metrics']['quiet']['gain']-.75)<1e-6 and row['observable_metrics_changed'] and not row['other_changed_controls'],result
    assert abs(result['rows'][0]['metrics']['quiet']['gain']-.25)<1e-6,result
    assert row['state_difference']['status']=='CANDIDATE' and row['state_difference']['stable_changed_bytes']>0,result
    delay=run_sweep(spec,'creative_delay',[0.,1.]);assert all(r['status']=='captured' for r in delay['rows']),delay
    assert delay['repeat_metrics_stable'] and delay['rows'][0]['metrics']['first_arrival']==0 and delay['rows'][-1]['metrics']['first_arrival']==137,delay
    assert delay['rows'][-1]['behavior_candidate']=='delay',delay
    # Common default state: gain .5 and creative_delay off. Repeat every changed point.
    mapping=run_parameter_map(spec,{'gain':[.5,.25,.75],'creative_delay':[0.,1.]})
    assert mapping['status']=='CANDIDATE',mapping
    controls={r['parameter']:r for r in mapping['mapping']['controls']}
    assert all(r['observed_state_byte_count']>0 and all(o['status']=='STATE_AND_AUDIO' for o in r['observations']) for r in controls.values()),mapping
    print('SKELL_OWNED_PARAMETER_MAP '+json.dumps(mapping['mapping'],sort_keys=True))
    # The analyzer front-end itself must be transparent at both block sizes.
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/'probes';root.mkdir();fs=48000;t=np.arange(4813)/fs
        x=np.column_stack((.2*np.sin(2*np.pi*997*t),.3*np.cos(2*np.pi*701*t))).astype(np.float32)
        source=root/'probe.wav';sf.write(source,x,fs,subtype='FLOAT')
        (root/'manifest.json').write_text(json.dumps({'schema':1,'sample_rate':fs,'cases':[{'id':'probe','family':'linear','file':source.name,'sha256':digest(source),'frames':len(x),'windows':[]}]}))
        spec={'backend':'installed_vst3','authorization':'installed_and_licensed','purpose':'owned_fixture','path':str(analyzer),'sha256':bundle_hash(analyzer),'version':'0.2.0','parameters':{},'expected_normalized':{},'target_stage':'output'}
        plan=[{'id':f'analyzer_{n}','case':'probe','spec':dict(spec,block_size=n)} for n in (64,1024)]
        out=Path(tmp)/'capture';rows=run_matrix(root,plan,out,authorized=True,timeout=90)
        assert all(r['status']=='captured' for r in rows),rows
        for r in rows:
            y,_=sf.read(out/r['id']/'render.wav',dtype='float32',always_2d=True)
            assert np.array_equal(y,x) and r['metadata']['reported_latency_samples']==0,r
    print('Owned fixture sweep, state delta, creative delay and analyzer pass-through passed.')


if __name__=='__main__':main()
