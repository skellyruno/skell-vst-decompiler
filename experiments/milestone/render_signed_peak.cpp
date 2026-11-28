#include "SignedPeakGuard.h"
#include <cstdio>
#include <cstdlib>
using namespace skell_signed_peak;
int main(int argc,char** argv){if(argc!=3)return 2;Guard<true> a;Guard<false> b;double fs=std::atof(argv[1]);a.prepare(fs);b.prepare(fs);bool split=std::atoi(argv[2])!=0;float x[2];std::size_t n;while((n=std::fread(x,sizeof(float),2,stdin))==2){auto y=split?a.process({x[0],x[1]}):b.process({x[0],x[1]});float z[2]={float(y[0]),float(y[1])};if(std::fwrite(z,sizeof(float),2,stdout)!=2)return 1;}return n||std::ferror(stdin)?1:0;}
