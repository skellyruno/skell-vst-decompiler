#include "../experiments/engine_lab/MultiDrainResearch.h"
#include <cassert>
#include <cstdio>
#include <random>
using namespace skell_lab;
int main(){std::mt19937 rng(112);std::uniform_real_distribution<double> u(-1,1);unsigned echoes=0,forced=0;double maxWait=0;
for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){
    MultiDrainDelay a,b;assert(a.prepare(fs,64,.2,.5,1));assert(b.prepare(fs,64,.2,.5,0));
    for(int i=0;i<=640;++i){auto y=a.process({i==0?1.:0,0},i<70?64:128);if(i>=64&&i%64==0){assert(std::abs(y.l-std::pow(.5,i/64-1))<1e-12);++echoes;}assert(y.r==0);}
    assert(a.prepare(fs,fs*.10+.5,.5,.95,1));assert(b.prepare(fs,fs*.10+.5,.5,.95,0));
    const int interval=int(fs*.075),total=interval*12;int since=0;double prev=0;
    for(int i=0;i<total;++i){const double d=fs*(.10+.005*(i/interval))+.5;if(d!=prev){since=i;prev=d;}Frame x{u(rng),u(rng)};const auto y=a.process(x,d),z=b.process(x,d);assert(std::isfinite(y.l)&&std::isfinite(y.r)&&std::abs(y.l)<256&&std::abs(y.r)<256);assert(z.l==x.l&&z.r==x.r);assert(a.liveBanks()<=4);if(a.activeDelay()!=d){maxWait=std::max(maxWait,1000*(i-since)/fs);assert(i-since<=int(fs*.051));}}
    assert(a.activeDelay()==prev);assert(a.forcedRetirements()>0);forced+=a.forcedRetirements();
}std::printf("six rates, %u exact old echoes, %u forced retirements, maximum pending wait %.6f ms\n",echoes,forced,maxWait);}
