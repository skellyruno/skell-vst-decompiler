// Independent lab variants only; never instantiated in a production plugin.
#include "../../experiments/engine_lab/ColorOversampled.h"
using namespace skell_lab;
template<class T> static void render(double fs,double wet,const double* in,double* out,unsigned n) {
    T engine;engine.prepare(fs,12,.12,wet,0);
    for(unsigned i=0;i<n;++i){const auto y=engine.process({in[2*i],in[2*i+1]});out[2*i]=y.l;out[2*i+1]=y.r;}
}
extern "C" int render_variant(int kind,double fs,double wet,const double* in,double* out,unsigned n) {
    if(!in || !out || !n || fs<8000 || fs>384000)return 0;
    switch(kind){
    case 0:render<ColorOversampled2x>(fs,wet,in,out,n);break;
    case 1:render<ColorOversampled>(fs,wet,in,out,n);break;
    case 2:render<ColorOversampledFixed<2,40,475>>(fs,wet,in,out,n);break;
    case 3:render<ColorOversampledFixed<4,40,475>>(fs,wet,in,out,n);break;
    case 4:render<ColorOversampledFixed<2,80,475>>(fs,wet,in,out,n);break;
    case 5:render<ColorOversampledFixed<4,80,475>>(fs,wet,in,out,n);break;
    default:return 0;
    }return 1;
}
