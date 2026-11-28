"""Measure owned native renders, not vendor equivalence."""
import sys,json,subprocess
import numpy as np
from skell_vst_decompiler.behavioral_metrics import block_gain,tone_products,sidebands
from skell_vst_decompiler.spectral_probe import measure
FS=48000

def run(exe):
    def rows(name,n,length=FS):
        return np.frombuffer(subprocess.check_output([exe,name]),dtype='<f4').reshape(n,length,4)
    report={}
    rec=[]
    for dur,v in zip((.04,.2,1.),rows('leveler',3,2*FS)):
        g=block_gain(FS,v[:,:2],v[:,2:],10)
        arr=np.asarray(g['gain']);assert np.max(np.abs(arr[:,0]-arr[:,1]))<1e-6
        # 95% return to unity, after the last below-threshold block.
        bad=np.flatnonzero(arr[:,0]<.95)
        rec.append({'drive_seconds':dur,'initial_gain':float(arr[0,0]),'recovery_95_ms':g['time_ms'][bad[-1]+1] if len(bad) and bad[-1]+1<len(arr) else None})
    assert rec[-1]['recovery_95_ms']>rec[0]['recovery_95_ms']
    report['leveler']=rec
    spectra=[]
    idx=0
    captures=rows('color',18)
    for hz in (1000,11000):
        for amp in (.1,.5,.9):
            for factor in (1,2,4):
                v=captures[idx];idx+=1
                products=tone_products(FS,hz,v[:,2:]);entries={r['hz']:r for r in products}
                fundamental=entries[hz]['amplitude'][0]
                fold={str(r['hz']):float(20*np.log10(max(r['amplitude'][0]/fundamental,1e-15))) for r in products if not r['ambiguous'] and r['origins'][0]['fold_candidate'] and r['hz']!=0}
                spectra.append({'hz':hz,'input_peak':amp,'oversampling':factor,'fundamental':fundamental,'peak':float(np.max(np.abs(v[:,2:]))),'fold_candidates_dbc':fold,'harmonic2_dbc':20*np.log10(max(entries[2*hz]['amplitude'][0]/fundamental,1e-15))})
    for amp in (.1,.5,.9):
        s=[r for r in spectra if r['hz']==11000 and r['input_peak']==amp]
        assert s[2]['fold_candidates_dbc']['15000']<s[0]['fold_candidates_dbc']['15000']-30
    report['color']=spectra
    present=[]
    p=rows('presence',4)
    for i,amp in enumerate((.04,.3)):
        z=measure(FS,(100,1000,9000),p[2*i,:,2:],p[2*i+1,:,2:]);present.append({'input_scale':amp,'gain_db':[x['channels'][0]['gain_db'] for x in z['tones']]})
    assert present[0]['gain_db'][2]>present[1]['gain_db'][2]
    report['presence']=present
    mod=[]
    for depth,v in zip((0.,.2,1.),rows('flang',3)):
        z=sidebands(FS,1000,4,v[:,2:],orders=12);mod.append({'depth_ms':depth,'carrier_amplitude':z[12]['amplitude'][0],'measured_sideband_power':sum(q['amplitude'][0]**2 for q in z if q['order'])})
    assert mod[0]['measured_sideband_power']<1e-12 and mod[1]['measured_sideband_power']>.001
    report['flang']=mod
    return report
if __name__=='__main__':
    print(json.dumps(run(sys.argv[1]),indent=2,allow_nan=False))
