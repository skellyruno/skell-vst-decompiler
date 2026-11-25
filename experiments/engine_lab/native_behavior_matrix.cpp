// Render original owned prototypes for independent behavioral diagnostics.
#include "IndependentEngines.h"
#include "ColorOversampled.h"
#include "../flangus_reference/StackedFlanger.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace skell_lab;
constexpr int fs=48000;
void emit(Frame in,Frame out){const float v[]={float(in.l),float(in.r),float(out.l),float(out.r)};if(std::fwrite(v,sizeof(float),4,stdout)!=4)std::exit(1);}
template<class T> void color(int hz,double amp){T p;p.prepare(fs,12,.12,1,0);for(int i=0;i<fs*2;++i){double x=amp*std::sin(2*pi*hz*i/fs);Frame in{x,x};auto out=p.process(in);if(i>=fs)emit(in,out);}}
int main(int argc,char** argv){if(argc!=2)return 2;
    if(!std::strcmp(argv[1],"leveler")){
        for(double duration:{.04,.2,1.}){ProgramLeveler p;p.prepare(fs,-18,4,4,120);const int n=int(duration*fs);for(int i=0;i<n+fs*2;++i){const double x=.5*std::sin(2*pi*1000*i/fs);const Frame in{i<n?x:.03*x,.03*x};auto out=p.process(in);if(i>=n)emit(in,out);}}
    }else if(!std::strcmp(argv[1],"color")){
        for(int hz:{1000,11000})for(double amp:{.1,.5,.9}){color<ColorEngine>(hz,amp);color<ColorOversampled2x>(hz,amp);color<ColorOversampled>(hz,amp);}
    }else if(!std::strcmp(argv[1],"presence")){
        for(double amp:{.04,.3})for(bool ref:{true,false}){PresenceEngine p;p.prepare(fs,2600,ref?0:3,-22,ref?0:.7,1);for(int i=0;i<fs*2;++i){double x=amp*(std::sin(2*pi*100*i/fs)+std::sin(2*pi*1000*i/fs)+std::sin(2*pi*9000*i/fs))/3.;Frame in{x,x};auto out=p.process(in);if(i>=fs)emit(in,out);}}
    }else if(!std::strcmp(argv[1],"flang")){
        for(double depth:{0.,.2,1.}){skell::StackedFlanger p;if(!p.prepare(fs))return 2;skell::FlangeSettings s;s.order=4;s.rateHz=4;s.depthMs=depth;s.spread=0;s.wet=1;s.dry=0;p.setParameters(s);p.reset();for(int i=0;i<fs*2;++i){float l=float(.3*std::sin(2*pi*1000*i/fs)),r=l;Frame in{l,r};p.process(l,r);if(i>=fs)emit(in,{l,r});}}
    }else return 2;
}
