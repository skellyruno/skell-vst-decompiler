import unittest
import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import lfilter, chirp
from skell_vst_decompiler.system_id import history,generate,envelope,predict,fit_history,transfer,formant_candidates,analyze,fit_reports
from skell_vst_decompiler.reference_lab import digest


class SystemIDTests(unittest.TestCase):
    def test_history_bounds_and_models(self):
        for fs in (44100,48000,96000):
            for held in (False,True,"test"):self.assertLess(np.max(abs(history(fs,held))),1.)
        fs=48000;n=480;p=[-24,.75,2,20,160]
        for dual in (False,True):
            def data(held):
                a=history(fs,held);x,_=envelope(a,a,fs);g=predict(x,p+[5,.6] if dual else p,dual)
                return envelope(a,a*np.repeat(10**(g/20),n)[:,None],fs)
            r=fit_history(data(False),data(True));self.assertEqual(r['dual_preferred'],dual)
            f=r['dual' if dual else 'single'];self.assertLess(f['holdout_rmse_db'],1e-6)
            self.assertAlmostEqual(f['release_ms'],160,places=4)
            if dual:self.assertAlmostEqual(f['slow_release_ms'],800,places=3)

    def test_known_fir(self):
        fs=48000;t=np.arange(4*fs)/fs;x=np.r_[.1*chirp(t,30,4,18000,method='logarithmic')*np.clip(np.minimum(t,4-t)*50,0,1),np.zeros(fs)]
        r=transfer(x,lfilter([.5,.25],[1],x),fs)
        for v in r:
            self.assertTrue(v['supported']);h=.5+.25*np.exp(-2j*np.pi*v['hz']/fs)
            self.assertAlmostEqual(v['magnitude_db'],20*np.log10(abs(h)),places=4)
            self.assertAlmostEqual(v['phase_deg'],np.angle(h,deg=True),places=4)
        self.assertTrue(all(v['phase_deg'] is None for v in transfer(x,np.zeros_like(x),fs)))

    def test_formant_candidates(self):
        fs=48000;x=np.zeros(fs);x[::400]=1
        for f,bw in [(700,90),(1200,100),(2500,140)]:
            rad=np.exp(-np.pi*bw/fs);x=lfilter([1],[1,-2*rad*np.cos(2*np.pi*f/fs),rad**2],x)
        rows=formant_candidates(x/max(abs(x)),fs)
        for f in (700,1200,2500):self.assertLess(min(abs(r['hz']-f) for r in rows),40)
        self.assertEqual(formant_candidates(np.zeros(fs),fs),[])

    def test_full_wav_pipeline(self):
        fs=48000
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'probes';m=generate(root,fs);reports=[]
            for c in m['cases'][:3]:
                a,_=sf.read(root/c['file'],always_2d=True);x,_=envelope(a,a,fs)
                b=a*np.repeat(10**(predict(x,[-24,.75,2,20,160])/20),480)[:,None]
                wet=Path(d)/(c['id']+'_wet.wav');sf.write(wet,b,fs,subtype='FLOAT')
                meta={'plugin':'owned control','version':'1','settings':'same','offset_samples':0,'source_sha256':c['sha256'],'render_sha256':digest(wet)}
                reports.append(analyze(root,c['id'],wet,meta))
                with self.assertRaises(ValueError):analyze(root,c['id'],wet,dict(meta,source_sha256='0'*64))
            result=fit_reports(*reports);self.assertLess(result['single']['holdout_rmse_db'],1e-5);self.assertLess(result['single']['test_rmse_db'],1e-5)
            reports[1]['metadata']['settings']='changed'
            with self.assertRaises(ValueError):fit_reports(*reports)

    def test_invalid_data(self):
        with self.assertRaises(ValueError):envelope(np.zeros((9600,2)),np.zeros((9600,2)),48000)
        with self.assertRaises(ValueError):fit_history(([0]*20,[0]*20),([0]*20,[0]*20))
        with self.assertRaises(ValueError):transfer(np.zeros(48000),np.zeros(48000),48000)


if __name__=='__main__':unittest.main()
