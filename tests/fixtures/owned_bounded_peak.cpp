#include "../../experiments/engine_lab/BoundedPeakResearch.h"
using namespace skell_lab;
extern "C" int bounded_peak(int mode,double fs,double release,const double* x,double* y,unsigned n){
    if(!x||!y||!n||mode<0||mode>2||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(release)||release<1||release>1000)return 0;
    BoundedPeakGuard g;g.prepare(fs,-1,release,mode);for(unsigned i=0;i<n+16;++i){auto z=g.process(i<n?Frame{x[2*i],x[2*i+1]}:Frame{0,0});if(i>=16){y[2*(i-16)]=z.l;y[2*(i-16)+1]=z.r;}}return 1;
}
