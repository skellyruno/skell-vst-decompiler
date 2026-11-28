// Native callback proxy only: one thread, no actual plugin host.
#include "../experiments/engine_lab/TransitionPeakResearch.h"
#include "../experiments/engine_lab/ColorSplitNative.h"
#include <chrono>
#include <fstream>
#include <iostream>
#include <iomanip>
using namespace skell_lab;
struct Chain { ColorSplitNative<4,40,450,475> color;ReconstructionGuard guard;TransitionDelay2 delay;
    void prepare(double fs){color.prepare(fs,12,.12,1,0);guard.prepare(fs,-1,60,false);if(!delay.prepare(fs,fs*.12+.5,.5,.7,1))throw std::runtime_error("prepare");}
    Frame process(Frame x,double d){auto y=color.process(x);auto z=delay.process(y,d);return guard.process(z);}
};
int main(int argc,char**argv){if(argc!=3)return 2;const double fs=std::stod(argv[2]);if(fs<8000||fs>384000)return 2;std::ifstream f(argv[1],std::ios::binary);std::vector<Frame>x;Frame v{};while(f.read(reinterpret_cast<char*>(&v),sizeof(v)))x.push_back(v);if(x.size()<128)return 2;
    std::cout<<std::setprecision(10);for(int n:{1,4,8,16}){std::vector<Chain> chains(n);for(auto&c:chains)c.prepare(fs);std::vector<double> times;double sum=0;const int blocks=512,block=128;for(int i=0;i<blocks+64;++i){const auto start=std::chrono::steady_clock::now();for(auto&c:chains)for(int j=0;j<block;++j){auto y=c.process(x[(i*block+j)%x.size()],fs*(i<256?.12:.18)+.5);if(!std::isfinite(y.l)||!std::isfinite(y.r))return 3;sum+=y.l+y.r;}const auto end=std::chrono::steady_clock::now();if(i>=64)times.push_back(std::chrono::duration<double,std::milli>(end-start).count());}std::sort(times.begin(),times.end());const double budget=128000/fs;std::cout<<n<<","<<times[times.size()/2]<<","<<times[std::size_t(.99*(times.size()-1))]<<","<<times.back()<<","<<std::count_if(times.begin(),times.end(),[&](double t){return t>budget;})<<","<<budget<<","<<sum<<"\n";}
}
