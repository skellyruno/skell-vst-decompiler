#include "RackColor.h"
#include <chrono>
#include <cstdio>
#include <random>
using namespace skell_milestone;
template<class G> double bench(const std::vector<Frame>& src){G g;g.prepare(48000);volatile double sink=0;auto t=std::chrono::steady_clock::now();for(auto x:src){auto y=g.process(x);sink+=y[0];}return std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count()*48/src.size();}
int main(){std::mt19937 rng(31);std::uniform_real_distribution<double> u(-1.8,1.8);std::vector<Frame> src(1000000);for(auto& x:src)x={u(rng),u(rng)};std::array<double,7>a{},b{};for(std::size_t i=0;i<a.size();++i){if(i%2){b[i]=bench<FastReconstructionGuard>(src);a[i]=bench<ReconstructionGuard>(src);}else{a[i]=bench<ReconstructionGuard>(src);b[i]=bench<FastReconstructionGuard>(src);}}std::sort(a.begin(),a.end());std::sort(b.begin(),b.end());std::printf("median us/48 stereo frames old %.6f new %.6f, change %.2f%%\n",a[3],b[3],100*(b[3]/a[3]-1));}
