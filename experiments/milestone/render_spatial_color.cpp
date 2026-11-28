#include "SpatialColor.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace skell_milestone;
int main(int argc,char** argv){if(argc!=3)return 2;const double fs=std::atof(argv[1]);const char* mode=argv[2];StereoSpace w;w.prepare(fs,3,6,200);ToneShape eq;eq.prepare(fs,100,5000,2,-1);VocalDouble d;d.prepare(fs,.35);DistancePan p;p.prepare(fs,-.65,3);Clip4x c;c.prepare(6,-1,.25);float f[2];size_t n;
while((n=std::fread(f,sizeof(float),2,stdin))==2){Frame x{f[0],f[1]},y{};if(!std::strcmp(mode,"width"))y=w.process(x);else if(!std::strcmp(mode,"eq"))y=eq.process(x);else if(!std::strcmp(mode,"double"))y=d.process(x);else if(!std::strcmp(mode,"pan"))y=p.process((x[0]+x[1])*.5);else if(!std::strcmp(mode,"clip"))y=c.process(x);else if(!std::strcmp(mode,"direct"))y=c.direct(x);else return 2;float o[2]={float(y[0]),float(y[1])};if(std::fwrite(o,sizeof(float),2,stdout)!=2)return 1;}return n||std::ferror(stdin)?1:0;}
