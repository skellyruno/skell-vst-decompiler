#include "../../experiments/engine_lab/ScheduledRecoveryGuard.h"
#include "../../experiments/engine_lab/BassAwarePeakGuard.h"
using namespace skell_lab;
extern "C" int scheduled_render(int mode,double fs,double rel,const double*x,double*y,unsigned n){
 if(!x||!y||!n||mode<0||mode>1||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(rel)||rel<1||rel>1000)return 0;
 ScheduledRecoveryGuard a;BassAwarePeakGuard b;a.prepare(fs,-1,rel);b.prepare(fs,-1,rel);
 for(unsigned i=0;i<n+16;++i){Frame v=i<n?Frame{x[2*i],x[2*i+1]}:Frame{};const auto z=mode?a.process(v):b.process(v);if(i>=16){y[2*(i-16)]=z.l;y[2*(i-16)+1]=z.r;}}return 1;
}
