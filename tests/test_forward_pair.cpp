#include "PairwiseRecoveryBound.h"
#include <cassert>
#include <random>
#include <cstdio>
int main(){std::mt19937_64 rng(720);std::uniform_real_distribution<double> u(0.,1.);unsigned long long checks=0;double worst=0.;for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.})for(double c:{.8912509381337456,.251188643150958})for(int i=0;i<10000;++i){std::array<double,17>w{},r{};for(unsigned j=0;j<17;++j){w[j]=8*u(rng)-4;r[j]=std::exp(-1/(fs*.001*(1+999*u(rng))));}const double cap=skell_lab::forwardPairCap<17>(w,r,c);assert(cap>=0&&cap<=1);for(int k=0;k<8;++k){double g=cap*u(rng),s=w[0]*g;for(unsigned j=1;j<17;++j){g=std::min(cap,r[j]*g+1-r[j])*u(rng);s+=w[j]*g;}worst=std::max(worst,s-c);assert(s<=c+1e-12);++checks;}}std::printf("%llu feasible gain sequence checks; worst positive excess %.17g\n",checks,worst);}
