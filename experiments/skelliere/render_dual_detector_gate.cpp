// Local-only float32 stereo stream renderer for owner-authorized aligned audio.
#include "OriginalDualDetectorGate.h"
#include <cstdio>
#include <cstdlib>
#include <string>
using namespace skell_lab;
int main(int argc,char**argv){
    if(argc!=7)return 2;
    try{
        DualDetectorGate g(std::stod(argv[1]),std::stod(argv[2]),std::stod(argv[3]),std::stod(argv[4]),std::stod(argv[5]),std::stod(argv[6]));
        float x[2];size_t n;
        while((n=std::fread(x,sizeof(float),2,stdin))==2){auto y=g.process({x[0],x[1]});float o[2]={float(y[0]),float(y[1])};if(std::fwrite(o,sizeof(float),2,stdout)!=2)return 1;}
        return n||std::ferror(stdin)?1:0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 2;}
}
