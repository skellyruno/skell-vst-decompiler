"""Fresh-process native fixture matrix with a separate train/validation/test fit."""
import json
from pathlib import Path
import tempfile
import soundfile as sf
from skell_vst_decompiler.host_capture import run_matrix
from skell_vst_decompiler.system_id import generate,analyze
from skell_vst_decompiler.detector_fit import compare_detector
from skell_vst_decompiler.divergence import first_difference


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/'probes';generate(root);out=Path(tmp)/'capture'
        settings={'threshold_db':-24,'ratio':4,'attack_ms':20,'release_ms':160}
        cases=('dynamic_train','dynamic_holdout','dynamic_test')
        plan=[{'id':f'{case}_{block}','case':case,'spec':{'backend':'fixture','name':'Compressor','parameters':settings,'block_size':block,'target_stage':'output'}} for block in (64,1024) for case in cases]
        plan.append(dict(plan[0],id='repeat_train'))
        results=run_matrix(root,plan,out)
        assert all(r['status']=='captured' for r in results),results
        by_id={r['id']:r for r in results};checks={}
        def read(name):return sf.read(out/name/'render.wav',always_2d=True)[0]
        for case in cases:
            a,b=read(f'{case}_64'),read(f'{case}_1024');checks[case]=first_difference(a,b,48000,atol=0,rtol=0)
        checks['fresh_process_repeat']=first_difference(read('dynamic_train_64'),read('repeat_train'),48000,atol=0,rtol=0)
        assert all(v['mismatched_samples']==0 for v in checks.values()),checks
        reports=[analyze(root,case,out/f'{case}_64'/'render.wav',by_id[f'{case}_64']['metadata']) for case in cases]
        model=compare_detector(*[(r['history']['levels_db'],r['history']['gain_db']) for r in reports])
        assert model['selected_by_validation']=='amplitude' and model['models']['amplitude']['test_rmse_db']<.15
        print('SKELL_HOST_CAPTURE_RESULT '+json.dumps({'captured':len(results),'block_sizes':[64,1024],'checks':checks,'model':model},sort_keys=True))


if __name__=='__main__':main()
