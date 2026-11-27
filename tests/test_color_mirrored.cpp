#include "../experiments/engine_lab/ColorSplitNative.h"
#include "../experiments/engine_lab/ColorSplitMirrored.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <limits>
#include <cstring>
using namespace skell_lab;
struct Results {unsigned long long channels=0,different=0;double worst=0;};
template<int F,int S,int U,int D> void check(double fs,bool strict,Results& result){
    std::mt19937 rng(86);std::uniform_real_distribution<double> u(-2,2);
    for(double wet:{0.,.5,1.})for(double drive:{0.,12.,24.}){
        ColorSplitNative<F,S,U,D> a;ColorSplitMirrored<F,S,U,D> b;a.prepare(fs,drive,.12,wet,0);b.prepare(fs,drive,.12,wet,0);
        for(int i=0;i<4096;++i){
            if(i==2049){a.reset();b.reset();}
            Frame x{u(rng),u(rng)};if(i==17)x.l=std::numeric_limits<double>::quiet_NaN();auto y=a.process(x),z=b.process(x);
            for(int ch=0;ch<2;++ch){const double p=ch?y.r:y.l,q=ch?z.r:z.l;assert(std::isfinite(p)&&std::isfinite(q));const double e=std::abs(p-q);++result.channels;
                if(e!=0){if(result.different++==0)std::fprintf(stderr,"first mismatch F=%d S=%d U=%d D=%d fs=%.0f wet=%.1f drive=%.0f frame=%d channel=%d reference=%.17g candidate=%.17g error=%.17g\n",F,S,U,D,fs,wet,drive,i,ch,p,q,e);result.worst=std::max(result.worst,e);}
                assert(e<=2e-12);if(wet==0||strict)assert(p==q);
            }
        }
    }
}
int main(int argc,char** argv){
    const bool strict=argc==1;assert(strict||(argc==2&&std::strcmp(argv[1],"--diagnostic-tolerance")==0));Results r;
    for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){check<2,40,450,450>(fs,strict,r);check<4,40,450,450>(fs,strict,r);check<4,40,450,475>(fs,strict,r);check<4,80,450,475>(fs,strict,r);}
    std::printf("%llu channel comparisons; %llu unequal; max %.17g; %s\n",r.channels,r.different,r.worst,strict?"strict exact":"diagnostic tolerance");
}
