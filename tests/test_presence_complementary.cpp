#include "../experiments/engine_lab/PresenceComplementary.h"
#include <cassert>
#include <cstdio>
#include <limits>
#include <random>
int main(){
    using namespace skell_lab;
    std::mt19937 rng(19);std::uniform_real_distribution<double> u(-1,1);
    for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.})for(double mix:{0.,.25,.5,.75,1.}){
        PresenceComplementary p;p.prepare(fs,2600,0,-22,0,mix);
        for(int i=0;i<4096;++i){Frame x{u(rng),u(rng)};auto y=p.process(x);assert(y.l==x.l&&y.r==x.r);}
        p.prepare(fs,2600,3,-22,.7,mix);
        for(int i=0;i<20000;++i){if(i%4093==0)p.reset();Frame x{u(rng),u(rng)};if(i==100)x.l=std::numeric_limits<double>::quiet_NaN();auto y=p.process(x);assert(std::isfinite(y.l)&&std::isfinite(y.r));if(mix==0)assert(y.l==skell_lab::finite(x.l)&&y.r==x.r);}
        PresenceComplementary a,b;a.prepare(fs);b.prepare(fs);for(int i=0;i<1024;++i){Frame x{u(rng),u(rng)};auto y=a.process(x),z=b.process({x.r,x.l});assert(y.l==z.r&&y.r==z.l);}
    }
    std::puts("Complementary presence: exact neutral/dry, finite/reset and stereo swap at six rates passed");
}
