#include "../../experiments/engine_lab/BassAwarePeakGuard.h"
#include "../../experiments/engine_lab/QuietFastPolarity.h"
#include "../../experiments/engine_lab/ColorCascadeResearch.h"
#include "../../experiments/engine_lab/ColorSplitSymmetric.h"
using namespace skell_lab;
template<class T> void color(double fs,const double*x,double*y,unsigned n){T e;e.prepare(fs,12,.12,1,0);for(unsigned i=0;i<n+40;++i){auto v=e.process(i<n?Frame{x[2*i],x[2*i+1]}:Frame{});if(i>=40){y[2*(i-40)]=v.l;y[2*(i-40)+1]=v.r;}}}
extern "C" int cascade_render(int mode,double fs,const double*x,double*y,unsigned n){if(!x||!y||!n||!std::isfinite(fs)||fs<8000||fs>384000)return 0;switch(mode){case 0:color<ColorSplitSymmetric<4,40,450,475>>(fs,x,y,n);break;case 1:color<ColorCascadeResearch<65,33>>(fs,x,y,n);break;case 2:color<ColorCascadeResearch<49,65>>(fs,x,y,n);break;default:return 0;}return 1;}
extern "C" int bass_guard(int mode,double fs,const double*x,double*y,unsigned n){if(!x||!y||!n||mode<0||mode>2||!std::isfinite(fs)||fs<8000||fs>384000)return 0;QuietFastPolarity fast,slow;BassAwarePeakGuard adapt;fast.prepare(fs,-1,1);slow.prepare(fs,-1,60);adapt.prepare(fs,-1,1);for(unsigned i=0;i<n+16;++i){Frame v=i<n?Frame{x[2*i],x[2*i+1]}:Frame{};auto z=mode==0?fast.process(v):mode==1?slow.process(v):adapt.process(v);if(i>=16){y[2*(i-16)]=z.l;y[2*(i-16)+1]=z.r;}}return 1;}
