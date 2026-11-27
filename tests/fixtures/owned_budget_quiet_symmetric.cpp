#include "../../experiments/engine_lab/PolarityPeakResearch.h"
#include "../../experiments/engine_lab/ReleaseSelectedGuard.h"
#include "../../experiments/engine_lab/MultiDrainResearch.h"
#include "../../experiments/engine_lab/BudgetedMultiDrainDelay.h"
#include "../../experiments/engine_lab/ColorSplitMirrored.h"
#include "../../experiments/engine_lab/ColorSplitSymmetric.h"
using namespace skell_lab;
extern "C" int research_guard(int mode,double fs,double rel,const double*x,double*y,unsigned n,double* stats){
    if(!x||!y||!n||!stats||mode<0||mode>3||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(rel)||rel<1||rel>1000)return 0;
    BoundedPeakGuard a;PolarityPeakGuard b;QuietFastPolarity c;ReleaseSelectedGuard d;a.prepare(fs,-1,rel,2);b.prepare(fs,-1,rel);c.prepare(fs,-1,rel);d.prepare(fs,-1,rel);
    for(unsigned i=0;i<n+16;++i){Frame v=i<n?Frame{x[2*i],x[2*i+1]}:Frame{};auto z=mode==0?a.process(v):mode==1?b.process(v):mode==2?c.process(v):d.process(v);if(i>=16){y[2*(i-16)]=z.l;y[2*(i-16)+1]=z.r;}}
    *stats=c.totalWindows()?double(c.skippedWindows())/c.totalWindows():0;return 1;
}
extern "C" int research_delay(int mode,double fs,const double*x,double*y,unsigned n){
    if(!x||!y||!n||mode<0||mode>1||!std::isfinite(fs)||fs<8000||fs>384000)return 0;
    MultiDrainDelay a;BudgetedMultiDrainDelay b;if(!a.prepare(fs,fs*.12+.5,1,.7,1)||!b.prepare(fs,fs*.12+.5,1,.7,1))return 0;
    const unsigned interval=unsigned(std::round(fs*.25));double target=fs*.12+.5;
    for(unsigned i=0;i<n;++i){if(i&&i%interval==0)target=fs*(.09+.015*((i/interval-1)%5))+.5;Frame x0{x[2*i],x[2*i+1]};auto z=mode?b.process(x0,target):a.process(x0,target);y[2*i]=z.l;y[2*i+1]=z.r;}return 1;
}
template<class T> void color(double fs,const double*x,double*y,unsigned n){T e;e.prepare(fs,12,.12,1,0);for(unsigned i=0;i<n;++i){auto z=e.process({x[2*i],x[2*i+1]});y[2*i]=z.l;y[2*i+1]=z.r;}}
extern "C" int research_color(int mode,double fs,const double*x,double*y,unsigned n){
    if(!x||!y||!n||mode<0||mode>1||!std::isfinite(fs)||fs<8000||fs>384000)return 0;
    if(mode)color<ColorSplitSymmetric<4,40,450,475>>(fs,x,y,n);else color<ColorSplitMirrored<4,40,450,475>>(fs,x,y,n);return 1;
}
