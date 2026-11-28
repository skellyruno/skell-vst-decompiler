#include "OriginalSpace.h"
#include <cstdio>
#include <string>
int main(int argc,char** argv){
    if(argc!=5)return 2;
    skell_lab::OriginalSpace r(std::stod(argv[1]),1.8,4200.,std::stod(argv[2]));
    FILE* in=std::fopen(argv[3],"rb");FILE* out=std::fopen(argv[4],"wb");if(!in||!out){if(in)std::fclose(in);if(out)std::fclose(out);return 3;}
    float x[2];int status=0;
    while(std::fread(x,sizeof(float),2,in)==2){auto y=r.wet({x[0],x[1]});float f[2]={float(y[0]),float(y[1])};if(std::fwrite(f,sizeof(float),2,out)!=2){status=4;break;}}
    if(std::ferror(in)||std::ferror(out))status=4;
    if(std::fclose(out))status=4;
    std::fclose(in);return status;
}
