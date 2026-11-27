#include "../../experiments/engine_lab/ColorSplitNative.h"
#include "../../experiments/engine_lab/ColorSplitMirrored.h"
using namespace skell_lab;
template<class E> void render(double fs,const double*x,double*y,unsigned n){E e;e.prepare(fs,12,.12,1,0);for(unsigned i=0;i<n;++i){auto v=e.process({x[2*i],x[2*i+1]});y[2*i]=v.l;y[2*i+1]=v.r;}}
extern "C" int mirrored_color(int mode,double fs,const double*x,double*y,unsigned n){
    if(!x||!y||!n||mode<0||mode>1||!std::isfinite(fs)||fs<8000||fs>384000)return 0;
    if(mode)render<ColorSplitMirrored<4,40,450,475>>(fs,x,y,n);else render<ColorSplitNative<4,40,450,475>>(fs,x,y,n);return 1;
}
