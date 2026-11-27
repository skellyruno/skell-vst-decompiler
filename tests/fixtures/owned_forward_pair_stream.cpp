#include "CachedScheduledGuard.h"
#include "PairwiseScheduledGuard.h"
using namespace skell_lab;
extern "C" int pair_stream(int mode,double fs,double release,const double* x,double* y,unsigned n){
    if(!x||!y||!n||mode<0||mode>1||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(release)||release<1||release>1000)return 0;
    CachedScheduledGuard a;PairwiseScheduledGuard b;a.prepare(fs,-1,release);b.prepare(fs,-1,release);
    for(unsigned i=0;i<n+16;++i){Frame v=i<n?Frame{x[2*i],x[2*i+1]}:Frame{};const auto z=mode?b.process(v):a.process(v);if(i>=16){y[2*(i-16)]=z.l;y[2*(i-16)+1]=z.r;}}return 1;
}
