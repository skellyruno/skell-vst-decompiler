#include "PreparedPairGuard.h"
#include "HistoryCapGuard.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <vector>
using namespace skell_lab;
int main(){std::mt19937 rng(719);std::uniform_real_distribution<double> u(-4,4);unsigned long long checks=0,improved=0;double maxPeak=0,minDelta=0;for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.})for(double rel:{1.,10.,60.})for(double ceilDb:{-1.,-12.}){
 PreparedPairGuard a;HistoryCapGuard b;a.prepare(fs,ceilDb,rel);b.prepare(fs,ceilDb,rel);std::vector<Frame> y(16,Frame{});
 for(int i=0;i<16000;++i){double v=i<4000?u(rng):i<8000?3*std::sin(2*pi*30*i/fs):i<12000?.01*u(rng):3*std::sin(2*pi*.43*i);Frame x{v,i<4000?u(rng):-.7*v};auto p=a.process(x),q=b.process(x);assert(std::isfinite(q.l)&&std::isfinite(q.r));minDelta=std::min({minDelta,std::abs(q.l)-std::abs(p.l),std::abs(q.r)-std::abs(p.r)});assert(std::abs(q.l)+1e-12>=std::abs(p.l)&&std::abs(q.r)+1e-12>=std::abs(p.r));improved+=(std::abs(q.l)>std::abs(p.l)+1e-12)+(std::abs(q.r)>std::abs(p.r)+1e-12);y.push_back(q);}
 for(int i=0;i<32;++i){y.push_back(b.process({}));}y.resize(y.size()+16,{});
 for(std::size_t i=0;i+17<=y.size();++i)for(const auto& h:b.kernel()){double l=0,r=0;for(int j=0;j<17;++j){l+=h[j]*y[i+j].l;r+=h[j]*y[i+j].r;}const double p=std::max(std::abs(l),std::abs(r));maxPeak=std::max(maxPeak,p);assert(p<=fromDb(ceilDb)+1e-12);checks+=2;}
 b.reset();for(int i=0;i<64;++i){auto q=b.process({.001,-.002});assert(q.l==(i<16?0:.001)&&q.r==(i<16?0:-.002));}}
 std::printf("%llu reconstruction checks; %llu improved channels; min delta %.17g; max peak %.17g\n",checks,improved,minDelta,maxPeak);}
