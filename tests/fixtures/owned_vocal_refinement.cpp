// Owned lab only. Presence wet-path trim and existing color ring parity.
#include "../../experiments/engine_lab/ColorContiguous.h"
#include "../../experiments/engine_lab/ColorOversampled.h"
using namespace skell_lab;
template<class T> static void color(double fs,double wet,double trim,const double* in,double* out,unsigned n) {
    T p;p.prepare(fs,12,.12,wet,trim);
    for(unsigned i=0;i<n;++i){auto y=p.process({in[2*i],in[2*i+1]});out[2*i]=y.l;out[2*i+1]=y.r;}
}
extern "C" int render_refinement(int kind,double fs,double wet,double trim,const double* in,double* out,unsigned n) {
    if(!in || !out || !n || !std::isfinite(fs) || fs<8000 || fs>384000 || !std::isfinite(wet) || wet<0 || wet>1 || !std::isfinite(trim) || trim< -18 || trim>18)return 0;
    if(kind==0 || kind==1){
        if(kind==0 && trim!=0)return 0;
        PresenceEngine p;p.prepare(fs,2600,3,-22,.7,kind==0?wet:1);
        const double g=fromDb(trim);
        for(unsigned i=0;i<n;++i){const Frame x{skell_lab::finite(in[2*i]),skell_lab::finite(in[2*i+1])};auto y=p.process(x);
            if(kind==1)y={x.l*(1-wet)+wet*g*y.l,x.r*(1-wet)+wet*g*y.r};
            out[2*i]=y.l;out[2*i+1]=y.r;
        }return 1;
    }
    switch(kind){
    case 2:color<ColorOversampled2x>(fs,wet,trim,in,out,n);break;
    case 3:color<ColorContiguous2x>(fs,wet,trim,in,out,n);break;
    case 4:color<ColorOversampled>(fs,wet,trim,in,out,n);break;
    case 5:color<ColorContiguous4x>(fs,wet,trim,in,out,n);break;
    default:return 0;
    }return 1;
}
