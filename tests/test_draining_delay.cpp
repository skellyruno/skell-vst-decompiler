#include "../experiments/engine_lab/DrainingDelayResearch.h"
#include <cassert>
#include <cstdio>
#include <random>
using namespace skell_lab;
int main(){std::mt19937 rng(90);std::uniform_real_distribution<double> u(-1,1);unsigned echoChecks=0;
    for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){
        DrainingDelay d;assert(d.prepare(fs,64,.1,.5,1));assert(d.tempoSamples(120,.125)==std::min(fs*.0625,std::floor(fs*.1)));assert(d.tempoSamples(120,1)==std::floor(fs*.1));
        const int samples=int(fs*.05)+64*11+512;for(int i=0;i<samples;++i){auto y=d.process({i==0?1.:0,0},i<70?64:128);if(i>=64&&i<=640&&i%64==0){assert(std::abs(y.l-std::pow(.5,i/64-1))<1e-12);++echoChecks;}assert(y.r==0);}
        assert(!d.busy()&&d.activeDelay()==128);
        DrainingDelay dry,wet;assert(dry.prepare(fs,64.5,.1,.95,0));assert(wet.prepare(fs,64.5,.1,.95,1));for(int i=0;i<50000;++i){Frame x{u(rng),u(rng)};const double request=i<1000?64.5:i<20000?128.25:256.75;const auto a=dry.process(x,request),b=wet.process(x,request);assert(a.l==x.l&&a.r==x.r);assert(std::isfinite(b.l)&&std::isfinite(b.r)&&std::abs(b.l)<128&&std::abs(b.r)<128);}
        DrainingDelay tempo;assert(tempo.prepare(fs,fs*.0625,2,.0,1));assert(std::abs(tempo.tempoSamples(120,.125)-fs*.0625)<1e-12);assert(std::abs(tempo.tempoSamples(90,.25)-fs/6)<1e-10);
        const auto change=tempo.tempoSamples(90,.25);tempo.process({},change);assert(tempo.activeDelay()==change&&tempo.busy());
    }
    std::printf("six rates: %u exact old-tail echo checks, tempo map, immediate target, dry and finite stress passed\n",echoChecks);
}
