import copy
import hashlib
import unittest
from skell_vst_decompiler.parameter_evidence import replicated_delta, summarize_map


def report(key, base, changed, audio=True, other=False):
    params={'gain':.5,'delay':0.,'dummy':.5}
    def row(raw, setting, metrics, values):
        return dict(status='captured',binary_sha256='a'*64,host_module_sha256='b'*64,version='1',state_sha256=hashlib.sha256(raw).hexdigest(),parameters=values,metrics=metrics,reported_latency=0,sample_rate=48000,value=setting)
    baseline=row(base,params[key],{'gain':.5},params)
    controls=dict(params);controls[key]=1.
    if other:controls['dummy']=0.
    point=row(changed,1.,{'gain':1. if audio else .5},controls)
    point.update(replicate_verified=True,state_difference=replicated_delta(base,base,changed,changed))
    return dict(parameter=key,repeat_changed=True,repeat_metrics_stable=True,rows=[baseline,copy.deepcopy(baseline),point,copy.deepcopy(point)])


class ParameterEvidenceTests(unittest.TestCase):
    def test_both_sides_repeated(self):
        r=replicated_delta(b'abcde',b'axcde',b'ABCDe',b'AByDe')
        self.assertEqual(r['spans'],[[0,1],[3,4]])
        self.assertEqual(r['unstable_bytes'],2)
        self.assertEqual(replicated_delta(b'a',b'a',b'aa',b'aa')['status'],'VARIABLE_LENGTH')
        r=replicated_delta(bytes(1000),bytes(1000),bytes(i%2 for i in range(1000)),bytes(i%2 for i in range(1000)))
        self.assertTrue(r['truncated']);self.assertEqual(len(r['spans']),256)

    def test_multi_control_map(self):
        r=summarize_map([report('gain',b'abc',b'ABc'),report('delay',b'abc',b'aBC'),report('dummy',b'abc',b'abC',False)])
        self.assertTrue(r['complete_comparison'])
        a,b,c=r['controls'];self.assertEqual(a['unshared_observed_byte_count'],1)
        self.assertEqual(b['shared_state_byte_count'],2)
        self.assertEqual(c['observations'][0]['status'],'STATE_ONLY')

    def test_wrong_baseline_rejected(self):
        with self.assertRaisesRegex(ValueError,'identical baseline'):
            summarize_map([report('gain',b'abc',b'Abc'),report('delay',b'xyz',b'xYz')])

    def test_confounded_and_unreplicated_excluded(self):
        a=report('gain',b'abc',b'Abc',other=True);b=report('delay',b'abc',b'aBc');b['rows'][2]['replicate_verified']=False
        r=summarize_map([a,b]);self.assertFalse(r['complete_comparison'])
        self.assertEqual(r['controls'][0]['observations'][0]['status'],'CONFOUNDED')
        self.assertEqual(r['controls'][1]['observations'][0]['status'],'UNRESOLVED')
        self.assertTrue(all(x['observed_state_byte_count']==0 for x in r['controls']))

if __name__=='__main__':unittest.main()
