#include "RackColor.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace skell_milestone;
int main(int argc,char** argv){if(argc!=3)return 2;double fs=std::atof(argv[1]);const char* mode=argv[2];SoftColor s;s.prepare(6,-4);ReconstructionGuard old;FastReconstructionGuard fast;old.prepare(fs);fast.prepare(fs);float f[2];size_t n;while((n=std::fread(f,sizeof(float),2,stdin))==2){Frame x{f[0],f[1]},y{};if(!std::strcmp(mode,"direct"))y=s.direct(x);else if(!std::strcmp(mode,"adaa"))y=s.process(x);else if(!std::strcmp(mode,"old"))y=old.process(x);else if(!std::strcmp(mode,"fast"))y=fast.process(x);else return 2;float o[2]={float(y[0]),float(y[1])};if(std::fwrite(o,sizeof(float),2,stdout)!=2)return 1;}return n||std::ferror(stdin)?1:0;}
