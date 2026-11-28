#include "../../experiments/engine_lab/LevelerPeakHold.h"
#include "../../experiments/engine_lab/LevelerSingleAttack.h"
#include "../../experiments/engine_lab/ColorOversampled.h"
#include "../../experiments/engine_lab/ColorResidualBypass.h"
#include "../../experiments/engine_lab/PresenceComplementary.h"
#include "ResearchDelay.h"
#include "ResearchAllpassDelay.h"
using namespace skell_lab;
template<class T> static void run(T& engine,const double* x,double* y,unsigned n){
    for(unsigned i=0;i<n;++i){auto v=engine.process({x[2*i],x[2*i+1]});y[2*i]=v.l;y[2*i+1]=v.r;}
}
extern "C" int render_tracks(int kind,double fs,double param,double wet,const double* x,double* y,unsigned n){
    if(!x||!y||!n||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(param)||!std::isfinite(wet)||wet<0||wet>1)return 0;
    switch(kind){
    case 0:{ProgramLeveler e;e.prepare(fs,-18,4,param,120,0,wet);run(e,x,y,n);break;}
    case 1:{LevelerSingleAttack e;e.prepare(fs,-18,4,param,120,0,wet);run(e,x,y,n);break;}
    case 2:{LevelerPeakHold e;e.prepare(fs,param,12,wet);run(e,x,y,n);break;}
    case 3:{ColorOversampled e;e.prepare(fs,12,.12,wet,0);run(e,x,y,n);break;}
    case 4:{ColorResidualBypass<4> e;e.prepare(fs,12,.12,wet,0,param);run(e,x,y,n);break;}
    case 5:{PresenceEngine e;e.prepare(fs,2600,3,-22,.7,wet);run(e,x,y,n);break;}
    case 6:{PresenceComplementary e;e.prepare(fs,2600,3,-22,.7,wet);run(e,x,y,n);break;}
    case 7:{skellay::research::ResearchDelay e;if(!e.prepare(fs,2,false))return 0;skellay::research::ResearchDelay::Controls p{1000*param/fs,.75f,float(wet),0};for(unsigned i=0;i<n;++i){auto v=e.process({float(x[2*i]),float(x[2*i+1])},p);y[2*i]=v.l;y[2*i+1]=v.r;}break;}
    case 8:{skellay::research::ResearchAllpassDelay e;if(!e.prepare(fs,param,.75,0,0,1,wet))return 0;run(e,x,y,n);break;}
    default:return 0;
    }return 1;
}
