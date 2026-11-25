// Synthetic held-out frequency sweep and independently assembled owned DSP chain.
#include "SpacerStereoSIMD.h"
#include "ColorContiguous.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cassert>
using namespace skell_lab;
void emit(float a,float b,float c,float d){const float v[]={a,b,c,d};if(std::fwrite(v,sizeof(float),4,stdout)!=4)std::exit(1);}
int main(int argc,char**argv){if(argc!=3)return 2;const int fs=std::atoi(argv[2]);if(fs!=44100&&fs!=48000&&fs!=96000&&fs!=192000)return 2;
 if(!std::strcmp(argv[1],"coverage")){
  // New frequencies deliberately include points between filter centers and beyond bank edges.
  for(int hz:{30,45,63,75,88,105,125,149,177,210,250,297,354,420,500,595,707,841,1000,1189,1414,1682,2000,2378,2828,3364,4000,4757,5657,6727,8000,9514,11314,13454,16000,19000}){
   SpacerStereoSIMD p;p.prepare(fs,{});double ei=0,eo=0,eq=0,ec=0;for(int i=0;i<fs;++i){double t=double(i)/fs;float x=float(.25*std::sin(2*pi*hz*t));float sc=float(.5*std::sin(2*pi*hz*t));auto y=p.tick(x,x,sc,0);if(i>=fs/2){ei+=double(x)*x;eo+=double(y[0])*y[0];eq+=double(y[1]-x)*(y[1]-x);ec+=double(y[0])*x;}}std::printf("%d %.9f %.9f %.9f\n",hz,10*std::log10(eo/ei),std::sqrt(eq/(fs-fs/2)),ec/ei);}
 }else if(!std::strcmp(argv[1],"chain")){
  // Fixed settings, headroom trim candidates; not a true-peak or automatic limiter.
  for(int stage:{0,1,2,3,4}){PresenceEngine presence;ProgramLeveler leveler;ColorContiguous4x color;
   presence.prepare(fs,2600,3,-22,.7,1);leveler.prepare(fs,-18,4,4,120);color.prepare(fs,12,.12,1,0);
   for(int i=0;i<2*fs;++i){double t=double(i)/fs;double env=(i<fs/2?.12:(i<fs?1.:(i<3*fs/2?.35:.8)));double x=env*(.48*std::sin(2*pi*110*t)+.32*std::sin(2*pi*997*t)+.22*std::sin(2*pi*11000*t));double r=env*(.46*std::sin(2*pi*127*t)+.31*std::sin(2*pi*1223*t)+.24*std::sin(2*pi*10999*t));if(i% (fs/10)==0){x+=.8;r-=.8;}Frame in{x,r},out=in;if(stage>=1)out=presence.process(out);if(stage>=2)out=leveler.process(out);if(stage>=3)out=color.process(out);if(stage>=4){out.l*=fromDb(-3);out.r*=fromDb(-3);}assert(std::isfinite(out.l)&&std::isfinite(out.r));emit(float(x),float(r),float(out.l),float(out.r));}
  }
 }else return 2;
}
