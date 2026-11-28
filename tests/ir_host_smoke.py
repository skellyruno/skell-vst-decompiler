"""Windows CI: render only our freshly built owned IR fixture, no vendor loading."""
import argparse,json,time
from pathlib import Path
import numpy as np
import pedalboard as pb
from scipy.signal import fftconvolve
from skell_vst_decompiler.host_capture import bundle_hash,windows_module_path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plugin',type=Path);a=p.parse_args();plugin=a.plugin.resolve();module=windows_module_path(plugin);sha=bundle_hash(plugin)
    if plugin.name!='Skell IR Host Fixture.vst3' or pb.__version__!='0.9.23':raise ValueError('owned fixture and pinned host required')
    results=[]
    for fs in (48000,96000):
        n=10*fs;i=np.arange(n,dtype=np.int64)[:,None];c=np.arange(4)[None,:];h=1e-5*((i*17+c*13)%31-15)/15.;h[0,[0,3]]+=.5
        x=np.zeros((2,n+fs),np.float32);x[:,:fs]=np.random.default_rng(919).uniform(-.2,.2,(2,fs));expected=np.zeros_like(x,dtype=np.float64)
        for o in range(2):
            for j in range(2):expected[o,:n+fs-1]+=fftconvolve(x[j,:fs].astype(float),h[:,o*2+j])
        for block in (64,128,512):
            fx=pb.load_plugin(str(module));assert fx.name=='Skell IR Host Fixture' and fx.reported_latency_samples==0
            t=time.perf_counter();y=fx.process(x.copy(),fs,buffer_size=block,reset=True);elapsed=time.perf_counter()-t
            assert y.shape==x.shape and np.isfinite(y).all();err=float(np.max(abs(y-expected)));assert err<2e-6,(fs,block,err)
            results.append(dict(rate=fs,block=block,max_abs_error=err,offline_host_seconds=elapsed,rendered_audio_seconds=len(x[0])/fs,reported_latency=fx.reported_latency_samples))
    assert bundle_hash(plugin)==sha
    print('SKELL_IR_HOST_RESULT '+json.dumps(dict(bundle_sha256=sha,results=results),sort_keys=True))
if __name__=='__main__':main()
