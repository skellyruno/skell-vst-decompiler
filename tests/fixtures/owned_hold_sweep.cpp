#include "../../experiments/engine_lab/IndependentEngines.h"
#include "../../experiments/engine_lab/LevelerPeakHold.h"
using namespace skell_lab;
template<class E> static void run(E& e,const double* x,double* y,unsigned n){
    for(unsigned i=0;i<n;++i){const auto v=e.process({x[2*i],x[2*i+1]});y[2*i]=v.l;y[2*i+1]=v.r;}
}
extern "C" int hold_sweep(int mode,double fs,double attack,double hold,const double* x,double* y,unsigned n){
    if(!x||!y||!n||mode<0||mode>1||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(attack)||attack<.1||attack>100||!std::isfinite(hold)||hold<0||hold>50)return 0;
    if(mode==0){ProgramLeveler e;e.prepare(fs,-18,4,attack,120,0,1);run(e,x,y,n);}
    else {LevelerPeakHold e;e.prepare(fs,attack,hold,1);run(e,x,y,n);}
    return 1;
}
