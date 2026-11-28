#include "../experiments/engine_lab/TransitionPeakResearch.h"
#include <cassert>
#include <cstdio>
#include <random>
using namespace skell_lab;
int main(){std::mt19937 rng(22);std::uniform_real_distribution<double> u(-2,2);double maxPeak=0;
for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){
    ReconstructionGuard g;g.prepare(fs);std::vector<Frame> y(16,{0,0});for(int i=0;i<10000;++i)y.push_back(g.process({u(rng),u(rng)}));for(int i=0;i<32;++i)y.push_back(g.process({0,0}));y.resize(y.size()+16,{0,0});
    for(std::size_t i=0;i+17<=y.size();++i)for(auto h:g.kernel()){double l=0,r=0;for(int j=0;j<17;++j){l+=h[j]*y[i+j].l;r+=h[j]*y[i+j].r;}maxPeak=std::max({maxPeak,std::abs(l),std::abs(r)});assert(maxPeak<=fromDb(-1)+1e-12);}
    g.reset();for(int i=0;i<40;++i){auto v=g.process({.01,-.02});assert(v.l==(i<16?0:.01)&&v.r==(i<16?0:-.02));}
    TransitionDelay2 a,b;assert(a.prepare(fs,64.5,.1,.95,1));assert(b.prepare(fs,64.5,.1,.95,0));
    for(int i=0;i<50000;++i){const double d=i<1000?64.5: i<20000?128.25:256.75;Frame x{u(rng),u(rng)};const auto p=a.process(x,d),q=b.process(x,d);assert(std::isfinite(p.l)&&std::isfinite(p.r));assert(std::abs(p.l)<128&&std::abs(p.r)<128);assert(q.l==x.l&&q.r==x.r);}assert(!a.busy()&&a.activeDelay()==256.75);
    TransitionDelay2 tail;assert(tail.prepare(fs,64,.1,.5,1));for(int i=0;i<200;++i){auto v=tail.process({i==0?1.:0,0},i<70?64:128);if(i==64)assert(v.l==1);if(i==128)assert(v.l==.5);}
}std::printf("six rates: reconstruction oracle max %.17g; exact delayed dry and transition stress passed\n",maxPeak);}
