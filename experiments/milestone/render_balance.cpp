#include "WetBalance.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace skell_balance;
// Input pairs are synchronized dry and independently rendered wet stereo frames.
int main(int argc,char** argv){if(argc!=4)return 2;WetBalance b;b.prepare(std::atof(argv[1]));b.setMix(std::atof(argv[2]));b.setEnabled(std::atoi(argv[3])!=0);b.reset();float x[4];size_t n;while((n=std::fread(x,sizeof(float),4,stdin))==4){auto y=b.process({x[0],x[1]},{x[2],x[3]});float z[2]={float(y[0]),float(y[1])};if(std::fwrite(z,sizeof(float),2,stdout)!=2)return 1;}return n||std::ferror(stdin)?1:0;}
