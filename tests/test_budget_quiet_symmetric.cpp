#include "../experiments/engine_lab/PolarityPeakResearch.h"
#include "../experiments/engine_lab/MultiDrainResearch.h"
#include "../experiments/engine_lab/ReleaseSelectedGuard.h"
#include "../experiments/engine_lab/BudgetedMultiDrainDelay.h"
#include "../experiments/engine_lab/ColorSplitSymmetric.h"
#include "../experiments/engine_lab/ColorSplitMirrored.h"
#include <cassert>
#include <cstdio>
#include <random>
using namespace skell_lab;
int main(){std::mt19937 rng(119);std::uniform_real_distribution<double> u(-4,4);unsigned long long exact=0,skipped=0;double maxError=0,peak=0;
for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){
    for(double rel:{1.,5.,10.,20.,60.,1000.}){PolarityPeakGuard p;p.prepare(fs,-1,rel);QuietFastPolarity q;q.prepare(fs,-1,rel);ReleaseSelectedGuard a;a.prepare(fs,-1,rel);BoundedPeakGuard b;b.prepare(fs,-1,rel,2);
        for(int i=0;i<6000;++i){Frame x{u(rng),u(rng)};if(i%1000<700){x.l*=.01;x.r*=.01;}if(i==3000){p.reset();q.reset();a.reset();b.reset();}auto y=p.process(x),z=q.process(x),s=a.process(x),t=b.process(x);assert(y.l==z.l&&y.r==z.r);assert(s.l==(rel<=10?z.l:t.l)&&s.r==(rel<=10?z.r:t.r));exact+=4;}skipped+=q.skippedWindows();assert(q.skippedWindows()>0);}
    WetBudget w;w.prepare(fs);for(int i=0;i<10000;++i){auto y=w.process({u(rng),u(rng)},{u(rng),u(rng)});peak=std::max({peak,std::abs(y.l),std::abs(y.r)});assert(peak<=fromDb(-1)+1e-12);}w.reset();auto y=w.process({.1,-.2},{-.03,.04});assert(y.l==.1-.03&&y.r==-.2+.04);
    BudgetedMultiDrainDelay d,e;MultiDrainDelay base;assert(d.prepare(fs,64.5,.1,.95,1)&&e.prepare(fs,64.5,.1,.95,0)&&base.prepare(fs,64.5,.1,.95,1));for(int i=0;i<20000;++i){double target=64.5+32*(i/(int(fs*.025)+1)%5);Frame x{u(rng),u(rng)};auto v=d.process(x,target),z=e.process(x,target);base.process(x,target);assert(std::abs(v.l)<=fromDb(-1)+1e-12&&std::abs(v.r)<=fromDb(-1)+1e-12);assert(z.l==x.l&&z.r==x.r);assert(d.activeDelay()==base.activeDelay()&&d.forcedRetirements()==base.forcedRetirements());}
    for(double mix:{0.,.5,1.})for(double drive:{0.,12.,24.}){ColorSplitMirrored<4,40,450,475> a;ColorSplitSymmetric<4,40,450,475> b;a.prepare(fs,drive,.12,mix,0);b.prepare(fs,drive,.12,mix,0);for(int i=0;i<4096;++i){if(i==2048){a.reset();b.reset();}Frame x{u(rng),u(rng)};auto y=a.process(x),z=b.process(x);maxError=std::max({maxError,std::abs(y.l-z.l),std::abs(y.r-z.r)});assert(maxError<2e-12);if(mix==0)assert(y.l==z.l&&y.r==z.r);}}
}std::printf("exact guard comparisons %llu; skipped %llu final-half windows; wet peak %.15g; symmetric max error %.15g\n",exact,skipped,peak,maxError);}
