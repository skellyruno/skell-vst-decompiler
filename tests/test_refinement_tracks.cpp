#include "../experiments/engine_lab/LevelerPeakHold.h"
#include "../experiments/engine_lab/LevelerSingleAttack.h"
#include "../experiments/engine_lab/ColorResidualBypass.h"
#include "../experiments/engine_lab/ColorOversampled.h"
#include <cassert>
#include <cstdio>
#include <random>
using namespace skell_lab;
int main(){
    std::mt19937 rng(91);std::uniform_real_distribution<double> u(-1,1);
    double maxParity=0;
    for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){
        LevelerPeakHold a,b;a.prepare(fs,4,12,0);b.prepare(fs,4,12,1);
        LevelerSingleAttack c;c.prepare(fs,-18,4,4,120,0,1);
        for(int i=0;i<int(fs*.1);++i){auto y=b.process({.5,.25}),z=c.process({.5,.25});assert(y.l==z.l&&y.r==z.r);}
        b.reset();LevelerPeakHold swapped;swapped.prepare(fs);
        for(int i=0;i<5000;++i){Frame x{u(rng),u(rng)};auto y=a.process(x),z=b.process(x),w=swapped.process({x.r,x.l});assert(y.l==x.l&&y.r==x.r);assert(z.l==w.r&&z.r==w.l);assert(std::isfinite(z.l)&&std::abs(z.l)<=std::abs(x.l)+1e-12);}
        for(double mix:{0.,.5,1.}){
            ColorOversampled base;ColorResidualBypass<4> zero,active;
            base.prepare(fs,12,.12,mix,0);zero.prepare(fs,12,.12,mix,0,0);active.prepare(fs,12,.12,mix,0,.25);
            Frame history[40]{};
            for(int i=0;i<3000;++i){Frame x{u(rng),u(rng)};auto y=base.process(x),z=zero.process(x),w=active.process(x);maxParity=std::max({maxParity,std::abs(y.l-z.l),std::abs(y.r-z.r)});assert(maxParity<=1e-12);assert(std::isfinite(w.l)&&std::isfinite(w.r));if(mix==0)assert(w.l==history[i%40].l&&w.r==history[i%40].r);history[i%40]=x;}
        }
    }
    std::printf("Six-rate crest-hold and residual color controls passed; max zero-correction difference %.17g\n",maxParity);
}
