"""Independent detector-domain alternatives for the 10ms reference histories."""
import numpy as np
from scipy.optimize import least_squares
from .system_id import fit_history


def predict_detector(levels,p,domain='amplitude'):
    """Constant-level blocks; integrate gain at 1ms substeps, not sample-accurate DSP."""
    if domain not in ('amplitude','power'):raise ValueError('Unknown detector domain')
    exponent=1 if domain=='amplitude' else 2
    threshold,slope,makeup,attack,release=p
    values=10**(np.asarray(levels)*exponent/20)
    # Reset detector to silence. A steady starting quiet segment establishes state.
    state=0.;out=[];starts=np.r_[0,np.flatnonzero(np.diff(values)!=0)+1,len(values)]
    for i,j in zip(starts[:-1],starts[1:]):
        target=values[i];tau=attack if target>state else release
        n=(j-i)*10
        v=target+(state-target)*np.exp(-np.arange(1,n+1)/tau)
        state=v[-1];env=20/exponent*np.log10(np.maximum(v,1e-15))
        gain=makeup-slope*np.maximum(0,env-threshold)
        out.extend(10*np.log10(np.mean(10**(gain.reshape(-1,10)/10),axis=1)))
    return np.asarray(out)


def compare_detector(train,validation,test):
    """Fit train only, choose by validation; preserve independent test scores."""
    pairs=[]
    for xx,yy in (train,validation,test):
        x,y=np.asarray(xx,float),np.asarray(yy,float)
        if x.ndim!=1 or x.shape!=y.shape or not 20<=len(x)<=12000 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or np.ptp(x)<12 or np.max(abs(x))>150 or np.max(abs(y))>150:raise ValueError('Invalid history')
        # Input levels measured from floating point WAVs fluctuate microscopically.
        # Round only the input level to 0.01 dB to group intended constant segments.
        pairs.append((np.round(x,2),y))
    (x,y),(xv,yv),(xt,yt)=pairs
    from .system_id import predict
    models=fit_history((x,y),(xv,yv))
    rm=lambda a,b:float(np.sqrt(np.mean((a-b)**2)))
    result={}
    for name in ('single','dual'):
        p=models[name]['parameters'];result[name]={'parameters':p,'train_rmse_db':models[name]['train_rmse_db'],'validation_rmse_db':models[name]['holdout_rmse_db'],'test_rmse_db':rm(predict(xt,p,name=='dual'),yt)}
    for domain in ('amplitude','power'):
        seeds=[[-24,.75,0,4,30],[-30,.5,0,25,200]]
        fits=[least_squares(lambda p:predict_detector(x,p,domain)-y,s,bounds=([-60,0,-24,.05,.05],[0,.98,24,200,1500]),max_nfev=200) for s in seeds]
        good=[f for f in fits if f.success]
        if not good:raise RuntimeError('Detector fit failed')
        p=min(good,key=lambda f:f.cost).x
        result[domain]={'parameters':p.tolist(),'train_rmse_db':rm(predict_detector(x,p,domain),y),'validation_rmse_db':rm(predict_detector(xv,p,domain),yv),'test_rmse_db':rm(predict_detector(xt,p,domain),yt)}
    chosen=min(result,key=lambda k:result[k]['validation_rmse_db'])
    return {'models':result,'selected_by_validation':chosen,'note':'Original descriptive models; detector times use e-folding convention, not knob mapping. No tuning on final test.'}


def main():
    import argparse
    import json
    from pathlib import Path
    from .system_id import fit_reports
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('train','validation','test'):p.add_argument(name)
    args=p.parse_args();reports=[json.loads(Path(getattr(args,k)).read_text()) for k in ('train','validation','test')]
    fit_reports(*reports)  # validates identities, settings, and the third history
    pairs=[(r['history']['levels_db'],r['history']['gain_db']) for r in reports]
    print(json.dumps(compare_detector(*pairs),indent=2,allow_nan=False))


if __name__=='__main__':main()
