#include "SpatialRefinement.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace skell_milestone;
int main(int argc,char** argv){if(argc<3)return 2;const double fs=std::atof(argv[1]);const char* mode=argv[2];GuardedWidth w;w.prepare(fs,3,6,200,-1,0);StereoSpace plain;plain.prepare(fs,3,6,200);MovingWobble m;double hz=.4,delay=7,depth=3,side=1.6,pan=.35;if(!std::strcmp(mode,"wobble")){if(argc!=8)return 2;hz=std::atof(argv[3]);delay=std::atof(argv[4]);depth=std::atof(argv[5]);side=std::atof(argv[6]);pan=std::atof(argv[7]);}m.prepare(fs,hz,delay,depth,side,pan,1.);Clip4x c;c.prepare(6,-1,.25);ReconstructionGuard g;g.prepare(fs,-1,.65,60);VocalDouble d;d.prepare(fs,.65);float f[2];size_t n;
while((n=std::fread(f,sizeof(float),2,stdin))==2){Frame x{f[0],f[1]},y{};if(!std::strcmp(mode,"wobble"))y=m.process(x);else if(!std::strcmp(mode,"width"))y=w.process(x);else if(!std::strcmp(mode,"plain"))y=plain.process(x);else if(!std::strcmp(mode,"clip"))y=c.process(x);else if(!std::strcmp(mode,"guard"))y=g.process(c.process(x));else if(!std::strcmp(mode,"double"))y=d.process(x);else return 2;float o[2]={float(y[0]),float(y[1])};if(std::fwrite(o,sizeof(float),2,stdout)!=2)return 1;}return n||std::ferror(stdin)?1:0;}
