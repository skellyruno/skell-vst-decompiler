#include "../experiments/engine_lab/AdaptiveResearch.h"
#include "../experiments/engine_lab/ColorOversampled.h"
#include "../experiments/engine_lab/ColorSplitNative.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <limits>
using namespace skell_lab;
int main(){
    std::mt19937 rng(104);std::uniform_real_distribution<double> u(-2,2);double error=0;
    for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){
        AdaptiveHold a,b;a.prepare(fs);b.prepare(fs);LinkedSampleGuard g;g.prepare(fs);
        ColorOversampled orig;ColorSplitNative<4> equal;ColorSplitNative<4,40,450,475> split;orig.prepare(fs,12,.12,1,0);equal.prepare(fs,12,.12,1,0);split.prepare(fs,12,.12,0,0);
        Frame dry[40]{};
        for(int i=0;i<8000;++i){if(i==4093){a.reset();b.reset();g.reset();}Frame x{u(rng),u(rng)};if(i==100)x.l=std::numeric_limits<double>::quiet_NaN();auto y=a.process(x),z=b.process({x.r,x.l}),w=g.process(x),p=orig.process(x),q=equal.process(x),d=split.process(x);
            assert(std::isfinite(y.l)&&std::isfinite(y.r)&&std::abs(y.l)<=std::abs(skell_lab::finite(x.l))+1e-12);assert(y.l==z.r&&y.r==z.l);
            assert(a.holdSamples()>=unsigned(std::round(fs*.002))&&a.holdSamples()<=unsigned(std::round(fs*.032)));assert(std::abs(w.l)<=fromDb(-1)+1e-12&&std::abs(w.r)<=fromDb(-1)+1e-12);
            error=std::max({error,std::abs(p.l-q.l),std::abs(p.r-q.r)});assert(error<=1e-12);assert(d.l==dry[i%40].l&&d.r==dry[i%40].r);dry[i%40]={skell_lab::finite(x.l),skell_lab::finite(x.r)};
        }
        for(double hz:{20.,50.,200.}){a.reset();for(int i=0;i<int(fs*.4);++i)a.process({.5*std::sin(2*pi*hz*i/fs),0});const double ms=1000*a.holdSamples()/fs;assert(std::abs(ms-std::clamp(575/hz,2.,32.))<=1000/fs*2);}
        g.reset();auto w=g.process({.1,-.2});assert(w.l==.1&&w.r==-.2);
    }
    for(double f:{.05,.25,.5,.75,.95}){FractionalAllpass2 a;assert(a.prepare(f));double energy=0,sum=0,firstMoment=0;for(int i=0;i<8192;++i){const double x=a.process(i==0?1:0);assert(std::isfinite(x));energy+=x*x;sum+=x;firstMoment+=i*x;}assert(std::abs(energy-1)<1e-12&&std::abs(sum-1)<1e-12&&std::abs(firstMoment-(1+f))<1e-10);a.reset();assert(a.process(0)==0);assert(!a.prepare(0));}
    std::printf("Six-rate adaptive hold, sample ceiling, dry latency, equal-cutoff parity (max %.17g), and allpass impulse checks passed\n",error);
}
