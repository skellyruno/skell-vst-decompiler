#include "../../experiments/engine_lab/CachedScheduledGuard.h"
#include "../../experiments/engine_lab/ScheduledRecoveryGuard.h"
#include "../../experiments/engine_lab/BandBudgetDelay.h"
#include "../../experiments/engine_lab/BudgetedMultiDrainDelay.h"
#include "../../experiments/engine_lab/RegularCrestHold.h"
using namespace skell_lab;
extern "C" int research_render(int mode,double fs,const double*x,double*y,unsigned n){
 if(!x||!y||!n||!std::isfinite(fs)||fs<8000||fs>384000||mode<0||mode>5)return 0;
 if(mode<2){CachedScheduledGuard a;ScheduledRecoveryGuard b;a.prepare(fs);b.prepare(fs);for(unsigned i=0;i<n+16;++i){Frame v=i<n?Frame{x[2*i],x[2*i+1]}:Frame{};auto z=mode?a.process(v):b.process(v);if(i>=16){y[2*(i-16)]=z.l;y[2*(i-16)+1]=z.r;}}}
 else if(mode<4){BandBudgetDelay a;BudgetedMultiDrainDelay b;if(!a.prepare(fs,fs*.12+.5,1,.7,1)||!b.prepare(fs,fs*.12+.5,1,.7,1))return 0;unsigned interval=unsigned(std::round(fs*.25));double target=fs*.12+.5;for(unsigned i=0;i<n;++i){if(i&&i%interval==0)target=fs*(.09+.015*((i/interval-1)%5))+.5;Frame v{x[2*i],x[2*i+1]};auto z=mode==3?a.process(v,target):b.process(v,target);y[2*i]=z.l;y[2*i+1]=z.r;}}
 else {AdaptiveHold a;RegularCrestHold b;const double attack=fs==44100?7.8342437744140625:fs==48000?7.8280181884765625:7.833101272583008;a.prepare(fs,attack);b.prepare(fs,attack);for(unsigned i=0;i<n;++i){Frame v{x[2*i],x[2*i+1]};auto z=mode==5?b.process(v):a.process(v);y[2*i]=z.l;y[2*i+1]=z.r;}}
 return 1;
}
