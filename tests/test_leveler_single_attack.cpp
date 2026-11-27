#include "../experiments/engine_lab/LevelerSingleAttack.h"
#include <cassert>
#include <cstdio>
#include <limits>
#include <random>
int main(){
    using namespace skell_lab;
    std::mt19937 rng(83);std::uniform_real_distribution<double> u(-1,1);
    for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){
        LevelerSingleAttack a,b;a.prepare(fs,-18,4,4,120,0,0);b.prepare(fs,-18,1,4,120,0,1);
        for(int i=0;i<20000;++i){Frame x{u(rng),u(rng)};if(i%4093==0){a.reset();b.reset();}if(i==7)x.r=std::numeric_limits<double>::infinity();auto y=a.process(x),z=b.process(x);assert(y.l==x.l&&y.r==skell_lab::finite(x.r));assert(z.l==y.l&&z.r==y.r);}
        a.prepare(fs,-18,4,4,120,0,1);b.prepare(fs,-18,4,4,120,0,1);
        for(int i=0;i<20000;++i){Frame x{u(rng),u(rng)};auto y=a.process(x),z=b.process({x.r,x.l});assert(y.l==z.r&&y.r==z.l);assert(std::isfinite(y.l)&&std::isfinite(y.r));assert(std::abs(y.l)<=std::abs(x.l)+1e-12);}
        a.reset();b.reset();ProgramLeveler original;original.prepare(fs,-18,4,4,120,0,1);
        const double want=std::pow(fromDb(-18)/.5,.75);Frame old{},next{};
        for(int i=0;i<int(fs*2);++i){old=original.process({.5,.25});next=a.process({.5,.25});assert(std::abs(next.l)<=std::abs(old.l)+1e-12);}
        assert(std::abs(old.l/.5-want)<1e-10&&std::abs(next.l/.5-want)<1e-10);
    }
    std::puts("Single attack leveler: dry/unity ratio, stereo swap, reset, finite and step oracle at six rates passed");
}
