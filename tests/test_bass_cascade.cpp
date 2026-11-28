#include "../experiments/engine_lab/BassAwarePeakGuard.h"
#include "../experiments/engine_lab/ColorCascadeResearch.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <vector>
using namespace skell_lab;
int main(){std::mt19937 rng(713);std::uniform_real_distribution<double> u(-4,4);unsigned long long checks=0;double maxPeak=0;
for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){
    for(double rel:{1.,10.,60.}){BassAwarePeakGuard g;g.prepare(fs,-1,rel);std::vector<Frame> y(16,Frame{});for(int i=0;i<12000;++i){double a=i<4000?u(rng):i<8000?3*std::sin(2*pi*50*i/fs):3*std::sin(2*pi*.43*i);y.push_back(g.process({a,-.7*a}));}for(int i=0;i<32;++i)y.push_back(g.process({}));y.resize(y.size()+16,{});
        for(std::size_t i=0;i+17<=y.size();++i)for(const auto& h:g.kernel()){double l=0,r=0;for(int j=0;j<17;++j){l+=h[j]*y[i+j].l;r+=h[j]*y[i+j].r;}maxPeak=std::max({maxPeak,std::abs(l),std::abs(r)});assert(maxPeak<=fromDb(-1)+1e-12);checks+=2;}}
    ColorCascadeResearch<> a,b;ColorCascadeResearch<49,65> c;a.prepare(fs,12,.12,0);b.prepare(fs);c.prepare(fs);Frame dry[40]{};
    for(int i=0;i<8192;++i){if(i==4096){a.reset();b.reset();c.reset();std::fill(std::begin(dry),std::end(dry),Frame{});}Frame x{u(rng),u(rng)};auto v=a.process(x),w=b.process(x),z=c.process(x);assert(v.l==dry[i%40].l&&v.r==dry[i%40].r);dry[i%40]=x;assert(std::isfinite(w.l)&&std::isfinite(w.r)&&std::isfinite(z.l)&&std::isfinite(z.r));}
    a.prepare(fs,12,.12,1);b.prepare(fs,12,.12,1);for(int i=0;i<4096;++i){Frame x{u(rng),u(rng)};auto v=a.process(x),w=b.process({x.r,x.l});assert(v.l==w.r&&v.r==w.l);}
}
std::printf("%llu adaptive finite-kernel checks; peak %.15g; six-rate cascade dry/reset/stereo passed\n",checks,maxPeak);
}
