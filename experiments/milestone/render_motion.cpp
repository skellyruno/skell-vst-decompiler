#include "MotionField.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace skell_milestone;
int main(int argc,char** argv){if(argc!=3&&argc!=4)return 2;MotionField m;const double fs=std::atof(argv[1]);m.prepare(fs);MotionField::Settings a,b;a.seconds=2.5;b.seconds=1.25;a.path=MotionField::Path::Orbit;b.path=MotionField::Path::Line;a.wave=MotionField::Wave::Ramp;b.wave=MotionField::Wave::Sine;a.depth=.5;b.depth=.25;a.farDb=-6;b.farDb=-3;a.travelDelayMs=12;b.predelayMs=7;b.start=.25;
if(!std::strcmp(argv[2],"phase")){a.path=b.path=MotionField::Path::PhaseOrbit;b.wave=MotionField::Wave::Ramp;}else if(!std::strcmp(argv[2],"pulse")){a.path=b.path=MotionField::Path::Pulse;}else if(!std::strcmp(argv[2],"trigger")){a.trigger=b.trigger=MotionField::Trigger::Return;a.thresholdDb=b.thresholdDb=-30;}else if(std::strcmp(argv[2],"orbit"))return 2;
m.set(0,a);m.set(1,b);m.setMix(.65);if(argc==4)m.setWetTrim(std::atof(argv[3]));m.reset();float x[2];size_t n;while((n=std::fread(x,sizeof(float),2,stdin))==2){auto y=m.process({x[0],x[1]});float o[2]={float(y[0]),float(y[1])};if(std::fwrite(o,sizeof(float),2,stdout)!=2)return 1;}return n||std::ferror(stdin)?1:0;}
