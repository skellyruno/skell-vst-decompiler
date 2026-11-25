"""Private aligned candidate comparisons with optional existing Skell tools."""
import argparse
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from .reference_lab import measure,digest


def compare(root,case,reference,candidate,ref_meta,cand_meta,*,sound_match=False,fif_signal=False,diagnose_first=False):
    """No automatic promotion, no gain correction or alignment inference."""
    if not isinstance(ref_meta.get('target_stage'),str) or not ref_meta['target_stage'].strip() or ref_meta['target_stage']!=cand_meta.get('target_stage'):
        raise ValueError('Explicit matching target stage required')
    r=measure(root,case,reference,ref_meta);c=measure(root,case,candidate,cand_meta)
    if r['source_sha256']!=c['source_sha256'] or r['sample_rate']!=c['sample_rate'] or r['frames']!=c['frames']:raise ValueError('Pairing mismatch')
    fs=r['sample_rate'];n=r['frames']
    a,_=sf.read(reference,start=ref_meta['offset_samples'],frames=n,always_2d=True)
    b,_=sf.read(candidate,start=cand_meta['offset_samples'],frames=n,always_2d=True)
    if digest(reference)!=r['render_sha256'] or digest(candidate)!=c['render_sha256']:raise ValueError('Render changed')
    rms=lambda x:float(np.sqrt(np.mean(x*x)))
    db=lambda x:float(20*np.log10(max(x,1e-15)))
    result={'case_id':case,'source_sha256':r['source_sha256'],'reference_sha256':r['render_sha256'],'candidate_sha256':c['render_sha256'],'sample_rate':fs,'frames':n,'target_stage':ref_meta['target_stage'],'relative_residual_db':db(rms(b-a)/max(rms(a),1e-15)) if rms(a)>1e-12 else None,'level_delta_db':db(rms(b))-db(rms(a)),'sound_match':{'status':'not_requested'},'fif_ears':{'status':'not_requested'},'note':'Operator-declared stage and alignment; diagnostic metrics only, never listening approval.'}
    if diagnose_first:
        from .divergence import first_difference
        result['divergence']=first_difference(a,b,fs)
    if sound_match:
        from skell_sound_match.quality_gate import measure as quality_measure
        result['sound_match']={'status':'measured','metrics':quality_measure(a,b,fs)}
    if fif_signal:
        from skell_sound_match.wav_only.vocal_knob_search import fif_ears_signal_snapshot
        result['fif_ears']={'status':'measured','reference':fif_ears_signal_snapshot(a,fs),'candidate':fif_ears_signal_snapshot(b,fs)}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('folder','case','reference','candidate','reference_metadata','candidate_metadata'):p.add_argument(name)
    p.add_argument('--sound-match',action='store_true');p.add_argument('--fif-signal',action='store_true');p.add_argument('--first-difference',action='store_true');a=p.parse_args()
    load=lambda x:json.loads(Path(x).read_text())
    print(json.dumps(compare(a.folder,a.case,a.reference,a.candidate,load(a.reference_metadata),load(a.candidate_metadata),sound_match=a.sound_match,fif_signal=a.fif_signal,diagnose_first=a.first_difference),indent=2,allow_nan=False))


if __name__=='__main__':main()
