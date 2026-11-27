#include "CachedScheduledGuard.h"
#include "PairwiseScheduledGuard.h"
#include <cassert>
#include <random>
#include <vector>
#include <cstdio>
using namespace skell_lab;
int main(){std::mt19937 rng(981);std::uniform_real_distribution<double> u(-4.,4.);unsigned long long checks=0;double minDelta=0,maxPeak=0;for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.})for(double rel:{1.,10.,60.})for(double ceilDb:{-1.,-12.}){CachedScheduledGuard a;PairwiseScheduledGuard b;a.prepare(fs,ceilDb,rel);b.prepare(fs,ceilDb,rel);std::vector<Frame> y(16,Frame{}),x(16,Frame{});for(int i=0;i<8192;++i){double v=i<2048?u(rng):i<4096?3*std::sin(2*pi*30*i/fs):i<6144?.01*u(rng):3*std::sin(2*pi*.43*i);Frame q{v,i<2048?u(rng):-.7*v};x.push_back(q);const auto old=a.process(q),now=b.process(q);assert(std::isfinite(now.l)&&std::isfinite(now.r));minDelta=std::min({minDelta,std::abs(now.l)-std::abs(old.l),std::abs(now.r)-std::abs(old.r)});assert(std::abs(now.l)+1e-12>=std::abs(old.l)&&std::abs(now.r)+1e-12>=std::abs(old.r));y.push_back(now);}for(int i=0;i<32;++i)y.push_back(b.process({}));y.resize(y.size()+16,{});for(size_t i=0;i+17<=y.size();++i)for(const auto& h:b.kernel()){double l=0,r=0;for(int j=0;j<17;++j){l+=h[j]*y[i+j].l;r+=h[j]*y[i+j].r;}maxPeak=std::max({maxPeak,std::abs(l),std::abs(r)});assert(std::max(std::abs(l),std::abs(r))<=fromDb(ceilDb)+1e-12);checks+=2;}b.reset();for(int i=0;i<64;++i){auto z=b.process({.001,-.002});assert(z.l==(i<16?0:.001)&&z.r==(i<16?0:-.002));}}std::printf("%llu reconstruction checks, max %.17g, min magnitude delta %.17g\n",checks,maxPeak,minDelta);}
