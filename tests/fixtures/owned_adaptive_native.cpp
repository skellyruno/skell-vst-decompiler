#include "../../experiments/engine_lab/AdaptiveResearch.h"
#include "../../experiments/engine_lab/LevelerPeakHold.h"
#include "../../experiments/engine_lab/ColorOversampled.h"
#include "../../experiments/engine_lab/ColorSplitNative.h"
using namespace skell_lab;
template<class T> void run(T& e,const double* x,double* y,unsigned n){for(unsigned i=0;i<n;++i){auto v=e.process({x[2*i],x[2*i+1]});y[2*i]=v.l;y[2*i+1]=v.r;}}
extern "C" int adaptive_native(int mode,double fs,double attack,const double* x,double* y,unsigned n){
    if(!x||!y||!n||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(attack))return 0;
    switch(mode){
    case 0:{ProgramLeveler e;e.prepare(fs,-18,4,4,120,0,1);run(e,x,y,n);break;}
    case 1:{LevelerPeakHold e;e.prepare(fs,attack,12,1);run(e,x,y,n);break;}
    case 2:{LevelerPeakHold e;e.prepare(fs,attack,20,1);run(e,x,y,n);break;}
    case 3:{AdaptiveHold e;e.prepare(fs,attack);run(e,x,y,n);break;}
    case 4:{ColorOversampled e;e.prepare(fs,12,.12,1,0);run(e,x,y,n);break;}
    case 5:{ColorSplitNative<4> e;e.prepare(fs,12,.12,1,0);run(e,x,y,n);break;}
    case 6:{ColorSplitNative<4,40,450,475> e;e.prepare(fs,12,.12,1,0);run(e,x,y,n);break;}
    case 7:{ColorSplitNative<4,40,475,450> e;e.prepare(fs,12,.12,1,0);run(e,x,y,n);break;}
    default:return 0;
    }return 1;
}
extern "C" int guard_native(double fs,const double* x,double* y,unsigned n){if(!x||!y||!n||!std::isfinite(fs)||fs<8000||fs>384000)return 0;LinkedSampleGuard g;g.prepare(fs);run(g,x,y,n);return 1;}
extern "C" int allpass2(double frac,double* y,unsigned n){if(!y||!n)return 0;FractionalAllpass2 e;if(!e.prepare(frac))return 0;for(unsigned i=0;i<n;++i)y[i]=e.process(i==0?1:0);return 1;}
