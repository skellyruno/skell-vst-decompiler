#include "../experiments/engine_lab/BoundedPeakResearch.h"
#include <cassert>
#include <cstdio>
#include <random>
using namespace skell_lab;
int main(){std::mt19937 rng(712);std::uniform_real_distribution<double> u(-4,4);double maxPeak[3]{};double signedMax=0;unsigned checks=0;
for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.})for(double release:{1.,60.,1000.})for(int signal=0;signal<3;++signal){
    std::vector<Frame> input;for(int i=0;i<4096;++i){double a=signal==0?u(rng):signal==1?2*std::sin(2*pi*.43*i)*(i%127<17?1:.08):(i%7==0?3.5:0);input.push_back({a,signal==0?u(rng):-.6*a});}
    for(int mode=0;mode<4;++mode){BoundedPeakGuard g;g.prepare(fs,-1,release,mode);ReconstructionGuard signedG;signedG.prepare(fs,-1,release,false);std::vector<Frame> y(16,{0,0});
        for(auto x:input){y.push_back(mode<3?g.process(x):signedG.process(x));}
        for(int i=0;i<32;++i){y.push_back(mode<3?g.process({0,0}):signedG.process({0,0}));}
        y.resize(y.size()+16,{0,0});
        for(std::size_t i=0;i+17<=y.size();++i)for(const auto& h:g.kernel()){double l=0,r=0;for(int j=0;j<17;++j){l+=h[j]*y[i+j].l;r+=h[j]*y[i+j].r;}const double p=std::max(std::abs(l),std::abs(r));if(mode<3){maxPeak[mode]=std::max(maxPeak[mode],p);assert(p<=fromDb(-1)+1e-12);checks+=2;}else signedMax=std::max(signedMax,p);}
    }
}
for(int mode=0;mode<3;++mode){BoundedPeakGuard g;g.prepare(48000,-1,60,mode);for(int i=0;i<100;++i){auto y=g.process({.01,-.02});assert(y.l==(i<16?0:.01)&&y.r==(i<16?0:-.02));}}
std::printf("%u reconstruction checks, absolute/lobe/prefix max %.12g %.12g %.12g; signed max %.12g\n",checks,maxPeak[0],maxPeak[1],maxPeak[2],signedMax);}
