#include "../../experiments/engine_lab/LevelerSingleAttack.h"
using namespace skell_lab;
template<class T> static void render(double fs,double attack,double mix,const double* x,double* y,unsigned n){
    T p;p.prepare(fs,-18,4,attack,120,0,mix);
    for(unsigned i=0;i<n;++i){auto z=p.process({x[2*i],x[2*i+1]});y[2*i]=z.l;y[2*i+1]=z.r;}
}
extern "C" int leveler_attack(int k,double fs,double attack,double wet,const double* x,double* y,unsigned n){
    if(!x||!y||!n||k<0||k>1||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(attack)||attack<.1||attack>100||!std::isfinite(wet)||wet<0||wet>1)return 0;
    if(k==0)render<ProgramLeveler>(fs,attack,wet,x,y,n);else render<LevelerSingleAttack>(fs,attack,wet,x,y,n);
    return 1;
}
