import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf
from skell_vst_decompiler.reference_lab import generate,measure,fit_curve,digest


class ReferenceLabTests(unittest.TestCase):
    def test_owned_compressor_fit_and_alignment(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'probes';m=generate(root);reports=[]
            self.assertEqual(len(m['cases']),11)
            for case in ('levels_train','levels_holdout'):
                c=next(c for c in m['cases'] if c['id']==case);x,fs=sf.read(root/c['file']);y=x.copy()
                for w in c['windows']:
                    lo=w['stop']-2*fs;hi=w['stop'];rms=20*np.log10(np.sqrt(np.mean(x[lo:hi]**2)));y[lo:hi]*=10**((2-.75*max(0,rms+24))/20)
                path=Path(d)/(case+'.wav');sf.write(path,np.pad(y,((17,0),(0,0))),fs,subtype='FLOAT')
                meta={'source_sha256':c['sha256'],'render_sha256':digest(path),'offset_samples':17,'plugin':'owned static fixture','version':'1','settings':'threshold -24 RMS dB, ratio 4, makeup 2'}
                r=measure(root,case,path,meta);reports.append(r)
                self.assertEqual(r['unused_tail_frames'],0)
                with self.assertRaises(ValueError):measure(root,case,path,{**meta,'source_sha256':'0'*64})
                with self.assertRaises(ValueError):measure(root,case,path,{**meta,'offset_samples':18})
            r=fit_curve(*reports);self.assertAlmostEqual(r['threshold_rms_db'],-24,places=4);self.assertAlmostEqual(r['ratio'],4,places=4);self.assertLess(r['heldout_rmse_db'],1e-5)
            print('SKELL_REFERENCE_LAB_RESULT',r)

    def test_identity_and_wrong_settings(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'probes';m=generate(root);c=next(c for c in m['cases'] if c['id']=='two_tone');meta={'source_sha256':c['sha256'],'render_sha256':c['sha256'],'offset_samples':0,'plugin':'owned identity','version':'1','settings':'identity'}
            r=measure(root,'two_tone',root/c['file'],meta);self.assertLess(r['relative_waveform_error_db'],-290);self.assertLess(r['selected_imd_db'],-140)
            with self.assertRaises(ValueError):measure(root,'two_tone',root/c['file'],{**meta,'settings':''})
            with self.assertRaises(ValueError):measure(root,'two_tone',root/'impulse.wav',meta)
            pitch=next(c for c in m['cases'] if c['id']=='pitch_steps')
            r=measure(root,'pitch_steps',root/pitch['file'],{**meta,'source_sha256':pitch['sha256'],'render_sha256':pitch['sha256']})
            self.assertGreater(len(r['pitch_trace']),300)
            self.assertTrue(all(abs(v['shift_cents'])<1e-9 for v in r['pitch_trace'] if v['shift_cents'] is not None))
            impulse=next(c for c in m['cases'] if c['id']=='impulse')
            r=measure(root,'impulse',root/impulse['file'],{**meta,'source_sha256':impulse['sha256'],'render_sha256':impulse['sha256']})
            self.assertEqual(r['impulse_response'][0]['peak_delay_samples'],[0,None])
            self.assertAlmostEqual(r['impulse_response'][0]['response_db']['1000'][0],0.)
            silent=Path(d)/'silent.wav';sf.write(silent,np.zeros((c['frames'],2)),m['sample_rate'],subtype='FLOAT')
            self.assertIsNone(measure(root,'two_tone',silent,{**meta,'render_sha256':digest(silent)})['selected_imd_db'])
            with self.assertRaises(FileExistsError):generate(root)
            with (root/c['file']).open('ab') as f:f.write(b'changed')
            with self.assertRaises(ValueError):measure(root,'two_tone',root/c['file'],meta)
    def test_pitch_and_dynamic_response(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'probes';m=generate(root);fs=m['sample_rate'];meta={'offset_samples':0,'plugin':'owned render fixture','version':'1','settings':'known synthetic response'}
            c=next(c for c in m['cases'] if c['id']=='pitch_steps');f=np.repeat([196.,220.,246.94,220.],fs)*2**(1/12);phase=2*np.pi*np.cumsum(f)/fs
            y=sum(.28/k*np.sin(k*phase) for k in range(1,5));wet=Path(d)/'pitch.wav';sf.write(wet,np.column_stack((y,y)),fs,subtype='FLOAT')
            r=measure(root,c['id'],wet,{**meta,'source_sha256':c['sha256'],'render_sha256':digest(wet)})
            stable=[v['shift_cents'] for v in r['pitch_trace'] if 200<v['frame_end_ms']%1000<900 and v['shift_cents'] is not None]
            self.assertGreater(len(stable),200);self.assertLess(max(abs(v-100) for v in stable),1)
            c=next(c for c in m['cases'] if c['id']=='history_steps');x,_=sf.read(root/c['file']);t=np.arange(len(x))/fs;reduction=np.zeros(len(t))
            # Known 150 ms exponential release on first low-level interval.
            mask=(t>=1.25)&(t<3.25);reduction[mask]=9*np.exp(-(t[mask]-1.25)/.15)
            wet=Path(d)/'history.wav';sf.write(wet,x*10**(-reduction[:,None]/20),fs,subtype='FLOAT')
            r=measure(root,c['id'],wet,{**meta,'source_sha256':c['sha256'],'render_sha256':digest(wet)})
            rows=[v for v in r['gain_curve'] if 1300<=v['time_ms']<=2000 and v['gain_db']<0];tau=-1/np.polyfit([v['time_ms'] for v in rows],np.log([-v['gain_db'] for v in rows]),1)[0]
            self.assertAlmostEqual(tau,150,delta=.1)
            print('SKELL_REFERENCE_DYNAMIC_RESULT',{'pitch_median_cents':float(np.median(stable)),'max_pitch_error_cents':float(max(abs(v-100) for v in stable)),'release_tau_ms':float(tau)})


if __name__=='__main__':unittest.main()
