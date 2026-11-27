#include "PairwiseRecoveryBound.h"
#include "ColorSplitSymmetric.h"
#include "ColorLiftedResearch.h"
#include "PairwiseScheduledGuard.h"
#include "PreparedPairGuard.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <limits>
using namespace skell_lab;
template<int F> void colorTest(double fs,unsigned long long& n,double (&maxErr)[3]){
    std::mt19937 rng(623);std::uniform_real_distribution<double> u(-2,2);
    for(double wet:{0.,.5,1.})for(double drive:{0.,12.,24.}){
        ColorSplitSymmetric<F,40,450,475> a;ColorLiftedResearch<F,40,450,475,1> b;ColorLiftedResearch<F,40,450,475,2> c;ColorLiftedResearch<F,40,450,475,3> d;
        a.prepare(fs,drive,.12,wet);b.prepare(fs,drive,.12,wet);c.prepare(fs,drive,.12,wet);d.prepare(fs,drive,.12,wet);
        for(int i=0;i<8192;++i){if(i==4096){a.reset();b.reset();c.reset();d.reset();}double v=i<1024?u(rng):i<2048?.5:i<3072?.7*std::sin(2*pi*20*i/fs):0.;Frame x{v,-.7*v};if(i==17)x.l=std::numeric_limits<double>::quiet_NaN();auto ref=a.process(x);Frame ys[]={b.process(x),c.process(x),d.process(x)};for(int j=0;j<3;++j){double err=std::max(std::abs(ref.l-ys[j].l),std::abs(ref.r-ys[j].r));assert(std::isfinite(err));maxErr[j]=std::max(maxErr[j],err);assert(err<=2e-10);if(wet==0)assert(ref.l==ys[j].l&&ref.r==ys[j].r);n+=2;}}
    }
}
int main(){unsigned long long n=0,exact=0,dual=0;double err[3]{};std::mt19937 rng(777);std::uniform_real_distribution<double> u(-4.,4.);
for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){colorTest<2>(fs,n,err);colorTest<4>(fs,n,err);for(double rel:{1.,10.,60.})for(double ceilDb:{-1.,-12.}){PairwiseScheduledGuard a;PreparedPairGuard b;a.prepare(fs,ceilDb,rel);b.prepare(fs,ceilDb,rel);for(int i=0;i<8192;++i){if(i==4096){a.reset();b.reset();}double v=i%4000<2000?u(rng):.01*u(rng);Frame x{v,-.7*v};auto y=a.process(x),z=b.process(x);assert(y.l==z.l&&y.r==z.r);exact+=2;}}
for(int i=0;i<10000;++i){std::array<double,17>w{},r{},p{};p[0]=1;for(int j=0;j<17;++j){w[j]=u(rng);r[j]=std::exp(-1/(fs*.001*(1+std::abs(u(rng))*10)));if(j)p[j]=p[j-1]*r[j];}assert(forwardPairCap<17>(w,r,.8912509381337456)==preparedPairCap<17>(w,p,.8912509381337456));++dual;}}
std::printf("%llu color channel checks, max %.17g %.17g %.17g; %llu exact stream channels, %llu exact dual checks\n",n,err[0],err[1],err[2],exact,dual);}
