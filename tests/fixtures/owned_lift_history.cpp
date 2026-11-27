#include "ColorSplitSymmetric.h"
#include "ColorLiftedResearch.h"
#include "PairwiseScheduledGuard.h"
#include "PreparedPairGuard.h"
#include "HistoryCapGuard.h"
using namespace skell_lab;
template<class T> void color(double fs,const double*x,double*y,unsigned n){T e;e.prepare(fs,12,.12,1,0);for(unsigned i=0;i<n;++i){auto v=e.process({x[2*i],x[2*i+1]});y[2*i]=v.l;y[2*i+1]=v.r;}}
extern "C" int lifted_color(int mode,double fs,const double*x,double*y,unsigned n){if(!x||!y||!n||!std::isfinite(fs)||fs<8000||fs>384000)return 0;switch(mode){case 0:color<ColorSplitSymmetric<4,40,450,475>>(fs,x,y,n);break;case 1:color<ColorLiftedResearch<4,40,450,475,1>>(fs,x,y,n);break;case 2:color<ColorLiftedResearch<4,40,450,475,2>>(fs,x,y,n);break;case 3:color<ColorLiftedResearch<4,40,450,475,3>>(fs,x,y,n);break;default:return 0;}return 1;}
template<class T> void guard(double fs,double rel,const double*x,double*y,unsigned n){T e;e.prepare(fs,-1,rel);for(unsigned i=0;i<n+16;++i){auto z=e.process(i<n?Frame{x[2*i],x[2*i+1]}:Frame{});if(i>=16){y[2*(i-16)]=z.l;y[2*(i-16)+1]=z.r;}}}
extern "C" int history_guard(int mode,double fs,double rel,const double*x,double*y,unsigned n){if(!x||!y||!n||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(rel)||rel<1||rel>1000)return 0;switch(mode){case 0:guard<PairwiseScheduledGuard>(fs,rel,x,y,n);break;case 1:guard<PreparedPairGuard>(fs,rel,x,y,n);break;case 2:guard<HistoryCapGuard>(fs,rel,x,y,n);break;default:return 0;}return 1;}
