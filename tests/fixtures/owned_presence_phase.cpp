#include "../../experiments/engine_lab/PresenceComplementary.h"
using namespace skell_lab;
template<class T> static void render(double fs,double boost,double amount,double wet,const double* x,double* y,unsigned n){
    T p;p.prepare(fs,2600,boost,-22,amount,wet);
    for(unsigned i=0;i<n;++i){auto v=p.process({x[2*i],x[2*i+1]});y[2*i]=v.l;y[2*i+1]=v.r;}
}
extern "C" int presence_phase(int k,double fs,double boost,double amount,double wet,const double* x,double* y,unsigned n){
    if(!x||!y||!n||k<0||k>1||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(boost)||!std::isfinite(amount)||!std::isfinite(wet))return 0;
    if(k==0)render<PresenceEngine>(fs,boost,amount,wet,x,y,n);else render<PresenceComplementary>(fs,boost,amount,wet,x,y,n);
    return 1;
}
