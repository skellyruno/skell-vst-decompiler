// Explicit output gain test of existing original lab color engines.
#include "../../experiments/engine_lab/ColorOversampled.h"
using namespace skell_lab;
template<class T> static void render(double fs,double db,const double* in,double* out,unsigned n) {
    T engine;engine.prepare(fs,12,.12,1,db);
    for(unsigned i=0;i<n;++i){auto y=engine.process({in[2*i],in[2*i+1]});out[2*i]=y.l;out[2*i+1]=y.r;}
}
extern "C" int render_color_gain(int k,double fs,double db,const double* in,double* out,unsigned n) {
    if(!in || !out || !n || !std::isfinite(fs) || fs<8000 || fs>384000 || !std::isfinite(db) || db< -18 || db>18)return 0;
    switch(k){
    case 0:render<ColorEngine>(fs,db,in,out,n);break;
    case 1:render<ColorOversampled2x>(fs,db,in,out,n);break;
    case 2:render<ColorOversampled>(fs,db,in,out,n);break;
    case 3:render<ColorOversampledFixed<2,40,475>>(fs,db,in,out,n);break;
    case 4:render<ColorOversampledFixed<4,40,475>>(fs,db,in,out,n);break;
    case 5:render<ColorOversampledFixed<2,80,475>>(fs,db,in,out,n);break;
    case 6:render<ColorOversampledFixed<4,80,475>>(fs,db,in,out,n);break;
    default:return 0;
    }return 1;
}
