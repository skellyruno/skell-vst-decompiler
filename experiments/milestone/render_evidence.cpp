#include "EvidenceEngines.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace skell_milestone;
int main(int argc,char** argv){if(argc<3)return 2;double fs=std::atof(argv[1]);const char* mode=argv[2];BoundedPeakGuard b;b.prepare(fs);FastReconstructionGuard f;f.prepare(fs);Clip4x c;c.prepare(6,-1,.25);TimedGate g;g.prepare(fs);if(!std::strcmp(mode,"gate")){if(argc!=9)return 2;g.setParameters(1,std::atof(argv[3]),std::atof(argv[4]),std::atof(argv[5]),std::atof(argv[6]),std::atof(argv[7]),std::atof(argv[8]));}float x[2];size_t n;while((n=std::fread(x,sizeof(float),2,stdin))==2){Frame v{x[0],x[1]},y{};if(!std::strcmp(mode,"gate")){double a=g.next(v[0],v[1]);y={a*v[0],a*v[1]};}else if(!std::strcmp(mode,"bound"))y=b.process(c.process(v));else if(!std::strcmp(mode,"fast"))y=f.process(c.process(v));else return 2;float out[2]={float(y[0]),float(y[1])};if(std::fwrite(out,sizeof(float),2,stdout)!=2)return 1;}return n||std::ferror(stdin)?1:0;}
