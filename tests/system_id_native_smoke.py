"""Actual built-in Pedalboard compressor, not a commercial target or loaded VST."""
import json
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf
import pedalboard
from skell_vst_decompiler.system_id import generate,analyze,fit_reports
from skell_vst_decompiler.detector_fit import compare_detector
from skell_vst_decompiler.reference_lab import digest


def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)/'probes';m=generate(root);reports=[]
        for c in m['cases'][:3]:
            a,_=sf.read(root/c['file'],always_2d=True)
            fx=pedalboard.Compressor(threshold_db=-24,ratio=4,attack_ms=20,release_ms=160)
            b=fx(a.T.astype('float32'),48000,reset=True).T
            wet=Path(d)/(c['id']+'_wet.wav');sf.write(wet,b,48000,subtype='FLOAT')
            meta=dict(plugin='Pedalboard built-in compressor',version=pedalboard.__version__,settings='threshold=-24 ratio=4 attack=20 release=160',offset_samples=0,source_sha256=c['sha256'],render_sha256=digest(wet))
            reports.append(analyze(root,c['id'],wet,meta))
        baseline=fit_reports(*reports)
        pairs=[(r['history']['levels_db'],r['history']['gain_db']) for r in reports]
        models=compare_detector(*pairs)
        assert models['selected_by_validation']=='amplitude'
        assert models['models']['amplitude']['test_rmse_db']<.15
        assert models['models']['amplitude']['test_rmse_db']<.5*models['models']['single']['test_rmse_db']
        print('SKELL_SYSTEM_ID_NATIVE_RESULT '+json.dumps(dict(pedalboard=pedalboard.__version__,baseline=baseline,comparison=models),sort_keys=True))


if __name__=='__main__':main()
