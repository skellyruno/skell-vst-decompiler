#include "../../experiments/engine_lab/DrainingDelayResearch.h"
#include "../../experiments/engine_lab/BoundedPeakResearch.h"
using namespace skell_lab;
extern "C" int drain_render(int mode,double fs,const double* x,double* y,unsigned n,double* events){
    if(!x||!y||!events||!n||mode<0||mode>1||!std::isfinite(fs)||fs<8000||fs>384000)return 0;
    DrainingDelay d;TransitionDelay2 b; if(!d.prepare(fs,fs*.12+.5,1,.7,1)||!b.prepare(fs,fs*.12+.5,1,.7,1))return 0;
    double prev=fs*.12+.5;int transitions=0;events[0]=events[1]=-1;
    for(unsigned i=0;i<n;++i){const double delay=fs*(i<n/3?.12:i<2*n/3?.18:.09)+.5;Frame z=mode?d.process({x[2*i],x[2*i+1]},delay):b.process({x[2*i],x[2*i+1]},delay);y[2*i]=z.l;y[2*i+1]=z.r;const double current=mode?d.activeDelay():b.activeDelay();if(current!=prev){if(transitions<2)events[transitions]=double(i);++transitions;prev=current;}}
    return 1;
}
