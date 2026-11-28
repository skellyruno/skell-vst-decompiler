import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from skell_vst_decompiler.ground_truth import rank,evaluate
from skell_vst_decompiler.analyzer_worker import state_difference,stimuli,describe,behavior_candidate,run_sweep,run_parameter_map

class GroundTruthAnalyzerTests(unittest.TestCase):
    def test_classifier_unknown_and_evaluation(self):
        train=[('gain',{'mulss':2}),('filter',{'addss':3})]
        self.assertEqual(rank({'mulss':2},train)['candidate'],'gain')
        self.assertIsNone(rank({'bitwise':30},train)['candidate'])
        self.assertEqual(evaluate({'a':'gain','b':None,'c':'filter'},{'a':'gain','b':None,'c':'gain'})['incorrect'],1)
        with self.assertRaises(ValueError):evaluate({'a':None},{'b':None})

    def test_state_delta_ignores_unstable_and_length(self):
        r=state_difference(b'abcde',b'axcde',b'ayCDE')
        self.assertEqual(r['spans'],[[2,5]])
        self.assertEqual(r['unstable_baseline_bytes'],1)
        self.assertEqual(state_difference(b'a',b'a',b'aa')['status'],'VARIABLE_LENGTH')
        a=bytes(1000);b=bytes(i%2 for i in range(1000))
        self.assertTrue(state_difference(a,a,b)['truncated'])
        self.assertEqual(len(state_difference(a,a,b)['spans']),256)

    def test_behavior_clipping_and_noop(self):
        p=stimuli();gain={k:x*.5 for k,x in p.items()}
        self.assertEqual(behavior_candidate(describe(p,gain)),'gain')
        self.assertEqual(behavior_candidate(describe(p,p)),'unresolved')
        clip={k:np.clip(x,-.2,.2) for k,x in p.items()}
        self.assertEqual(behavior_candidate(describe(p,clip)),'level_dependent_no_observed_memory')
        with self.assertRaises(ValueError):describe(p,{'impulse':p['impulse']})

    def test_sweep_fresh_jobs_and_state_mapping(self):
        spec={'sha256':'a'*64,'version':'1.0.0'};calls=[]
        def child(args,**kwargs):
            job,out,state=map(Path,args[-3:]);s=json.loads(job.read_text());v=s['normalized'];calls.append(v)
            raw=bytes([int(v*100),2]);state.write_bytes(raw)
            out.write_text(json.dumps({'state_sha256':hashlib.sha256(raw).hexdigest(),'binary_sha256':spec['sha256'],'version':spec['version'],'parameters':{'gain':v},'metrics':{'gain':v}}))
        with patch('skell_vst_decompiler.analyzer_worker.subprocess.run',side_effect=child):
            r=run_sweep(spec,'gain',[.25,.75])
        self.assertEqual(calls,[.25,.25,.75]);self.assertTrue(r['repeat_metrics_stable'])
        self.assertEqual(r['rows'][2]['state_difference']['spans'],[[0,1]])
        self.assertTrue(r['rows'][2]['observable_metrics_changed'])
        with self.assertRaises(ValueError):run_sweep(spec,'gain',[.25,.25])

    def test_repeat_changed_rejects_unstable_audio(self):
        spec={'sha256':'a'*64,'version':'1.0.0'}
        calls=[]
        def child(args,**kwargs):
            job,out,state=map(Path,args[-3:]);v=json.loads(job.read_text())['normalized'];calls.append(v)
            raw=bytes([int(v*100),len(calls)%2]);state.write_bytes(raw)
            out.write_text(json.dumps({'state_sha256':hashlib.sha256(raw).hexdigest(),'binary_sha256':spec['sha256'],'version':spec['version'],'parameters':{'gain':v},'metrics':{'gain':v if len(calls)!=6 else .9}}))
        with patch('skell_vst_decompiler.analyzer_worker.subprocess.run',side_effect=child):
            r=run_sweep(spec,'gain',[.25,.5,.75],repeat_changed=True)
        self.assertEqual(calls,[.25,.25,.5,.5,.75,.75])
        self.assertTrue(r['rows'][2]['replicate_verified'])
        self.assertEqual(r['rows'][2]['state_difference']['spans'],[[0,1]])
        self.assertFalse(r['rows'][4]['replicate_verified'])
        self.assertNotIn('state_difference',r['rows'][4])

    def test_map_prevalidates_all_points(self):
        with patch('skell_vst_decompiler.analyzer_worker.run_sweep') as sweep:
            with self.assertRaises(ValueError):run_parameter_map({}, {'good':[0.,1.],'bad':[0.,2.]})
            sweep.assert_not_called()
