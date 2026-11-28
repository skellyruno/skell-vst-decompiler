#include "../experiments/engine_lab/CachedScheduledGuard.h"
#include "../experiments/engine_lab/ScheduledRecoveryGuard.h"
#include "../experiments/engine_lab/BandBudgetDelay.h"
#include "../experiments/engine_lab/BudgetedMultiDrainDelay.h"
#include "../experiments/engine_lab/RegularCrestHold.h"
#include <cassert>
#include <cstdio>
#include <random>
using namespace skell_lab;
int main(){std::mt19937 rng(1123);std::uniform_real_distribution<double> u(-4,4);unsigned long long parity=0,peakChecks=0;double maxPeak=0;
for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){
 for(double rel:{1.,10.,60.})for(double ceilDb:{-1.,-12.}){
  CachedScheduledGuard a;ScheduledRecoveryGuard b;a.prepare(fs,ceilDb,rel);b.prepare(fs,ceilDb,rel);std::vector<Frame> y(16,Frame{});
  for(int i=0;i<16000;++i){double v=i<4000?u(rng):i<8000?3*std::sin(2*pi*30*i/fs):i<12000?.01*u(rng):3*std::sin(2*pi*.43*i);Frame x{v,i<4000?u(rng):-.7*v};const auto z=a.process(x),q=b.process(x);assert(std::isfinite(z.l)&&std::isfinite(z.r)&&z.l==q.l&&z.r==q.r);parity+=2;y.push_back(z);}
  for(int i=0;i<32;++i){auto z=a.process({}),q=b.process({});assert(z.l==q.l&&z.r==q.r);parity+=2;y.push_back(z);}y.resize(y.size()+16,{});
  for(std::size_t i=0;i+17<=y.size();++i)for(const auto& h:a.kernel()){double l=0,r=0;for(int j=0;j<17;++j){l+=h[j]*y[i+j].l;r+=h[j]*y[i+j].r;}assert(std::max(std::abs(l),std::abs(r))<=fromDb(ceilDb)+1e-12);peakChecks+=2;}
  a.reset();b.reset();for(int i=0;i<64;++i){auto z=a.process({.001,-.002}),q=b.process({.001,-.002});assert(z.l==q.l&&z.r==q.r);parity+=2;}
 }
 BandTailBudget budget;budget.prepare(fs);for(int i=0;i<12000;++i){auto y=budget.process({u(rng),u(rng)},{u(rng),u(rng)});maxPeak=std::max({maxPeak,std::abs(y.l),std::abs(y.r)});assert(maxPeak<=fromDb(-1)+1e-12);}budget.reset();auto q=budget.process({.1,-.2},{-.03,.04});assert(q.l==.1-.03&&q.r==-.2+.04);
 BandBudgetDelay d,dry;BudgetedMultiDrainDelay base;assert(d.prepare(fs,64.5,.1,.95,1)&&dry.prepare(fs,64.5,.1,.95,0)&&base.prepare(fs,64.5,.1,.95,1));for(int i=0;i<30000;++i){double target=64.5+32*(i/(int(fs*.025)+1)%5);Frame x{u(rng),u(rng)};auto z=d.process(x,target),q0=dry.process(x,target);base.process(x,target);assert(std::max(std::abs(z.l),std::abs(z.r))<=fromDb(-1)+1e-12);assert(q0.l==x.l&&q0.r==x.r&&d.activeDelay()==base.activeDelay()&&d.forcedRetirements()==base.forcedRetirements());}
 RegularCrestHold a,b;a.prepare(fs);b.prepare(fs);for(int i=0;i<int(fs*.5);++i){Frame x{.5*std::sin(2*pi*20*i/fs),.2*std::sin(2*pi*20*i/fs)};auto z=a.process(x),q0=b.process({x.r,x.l});assert(z.l==q0.r&&z.r==q0.l&&std::abs(z.l)<=std::abs(x.l)+1e-12);}assert(std::abs(1000*a.holdSamples()/fs-28.75)<=2000/fs);a.reset();assert(a.holdSamples()==unsigned(std::round(fs*.002)));
}
std::printf("%llu exact parity channels, %llu reconstruction checks, band budget max %.17g; scheduling, dry and crest hold passed\n",parity,peakChecks,maxPeak);}
