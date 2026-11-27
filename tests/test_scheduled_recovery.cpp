#include "../experiments/engine_lab/ScheduledRecoveryGuard.h"
#include "../experiments/engine_lab/BassAwarePeakGuard.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <vector>
using namespace skell_lab;
int main(){std::mt19937 rng(917);std::uniform_real_distribution<double> u(-4,4);unsigned long long checks=0;double peak=0,minimumGainDelta=0;
for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.})for(double rel:{1.,10.,60.})for(double ceilDb:{-1.,-12.}){
 ScheduledRecoveryGuard a;BassAwarePeakGuard b;a.prepare(fs,ceilDb,rel);b.prepare(fs,ceilDb,rel);
 std::vector<Frame> y(16,Frame{}),src(16,Frame{});
 for(int i=0;i<16000;++i){double x=i<4000?u(rng):i<8000?3*std::sin(2*pi*30*i/fs):i<12000?3*std::sin(2*pi*.43*i):.5*std::sin(2*pi*50*i/fs)+u(rng)*.8;Frame v{x,i<4000?u(rng):-.7*x};src.push_back(v);auto z=a.process(v),q=b.process(v);y.push_back(z);auto in=src[src.size()-17];assert(std::isfinite(z.l)&&std::isfinite(z.r));
 if(std::abs(in.l)>1e-9){double diff=z.l/in.l-q.l/in.l;minimumGainDelta=std::min(minimumGainDelta,diff);assert(diff>=-1e-12);}}
 for(int i=0;i<32;++i){y.push_back(a.process({}));}y.resize(y.size()+16,{});
 for(std::size_t i=0;i+17<=y.size();++i)for(const auto& h:a.kernel()){double l=0,r=0;for(int j=0;j<17;++j){l+=h[j]*y[i+j].l;r+=h[j]*y[i+j].r;}double p=std::max(std::abs(l),std::abs(r));peak=std::max(peak,p);assert(p<=fromDb(ceilDb)+1e-12);checks+=2;}
 a.reset();for(int i=0;i<64;++i){auto z=a.process({.001,-.002});assert(z.l==(i<16?0:.001)&&z.r==(i<16?0:-.002));}
}
std::printf("%llu checks, max peak %.17g; minimum gain delta %.17g; delayed dry exact\n",checks,peak,minimumGainDelta);
}
