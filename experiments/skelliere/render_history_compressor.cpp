// Local owner-audio stereo float32 renderer; no private inputs in Git or CI.
#include "OriginalHistoryCompressor.h"
#include <cstdio>
#include <string>
int main(int argc,char** argv){
    if(argc!=6)return 2;
    try{
        skell_lab::HistoryCompressor c(std::stod(argv[1]),std::stod(argv[2]),std::stod(argv[3]),std::stod(argv[4]),std::stod(argv[5]));
        float f[2];size_t n;
        while((n=std::fread(f,sizeof(float),2,stdin))==2){auto x=c.process({f[0],f[1]});float o[2]={float(x[0]),float(x[1])};if(std::fwrite(o,sizeof(float),2,stdout)!=2)return 1;}
        return n||std::ferror(stdin)?1:0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 2;}
}
