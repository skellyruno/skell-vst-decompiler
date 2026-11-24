#include "OriginalDynamics.h"
#include <cstdio>
#include <cstdlib>
#include <string>
int main(int argc,char** argv){
    if(argc!=5)return 2;
    const std::string mode=argv[1];const double fs=std::stod(argv[2]);
    if(mode!="baseline"&&mode!="lookahead"&&mode!="bell"&&mode!="static_bell"&&mode!="lookahead_margin")return 2;
    FILE* in=std::fopen(argv[3],"rb");FILE* out=std::fopen(argv[4],"wb");if(!in||!out){if(in)std::fclose(in);if(out)std::fclose(out);return 3;}
    skell_lab::BaselineLimiter base(fs);skell_lab::LookaheadLimiter limiter(fs,mode=="lookahead_margin"?-1.25:-1.);skell_lab::DynamicBell bell(fs);skell_lab::StaticBell fixed(fs);
    const auto delay=(mode=="lookahead"||mode=="lookahead_margin")?limiter.latency():0;std::size_t count=0;float buf[2];double maxReduction=0;
    auto emit=[&](skell_lab::Frame f){float y[2]={float(f[0]),float(f[1])};return std::fwrite(y,sizeof(float),2,out)==2;};
    while(std::fread(buf,sizeof(float),2,in)==2){
        skell_lab::Frame f{buf[0],buf[1]};
        if(mode=="baseline")f=base.process(f);else if(mode=="lookahead"||mode=="lookahead_margin")f=limiter.process(f);else if(mode=="static_bell")f=fixed.process(f);else {f=bell.process(f);maxReduction=std::min(maxReduction,bell.reductionDb());}
        if(count>=delay&&!emit(f)){std::fclose(in);std::fclose(out);return 4;}++count;
    }
    if(std::ferror(in)||std::ferror(out)){std::fclose(in);std::fclose(out);return 4;}
    for(std::size_t j=0;j<delay;++j){auto f=limiter.process({});if(count+j>=delay&&!emit(f)){std::fclose(in);std::fclose(out);return 4;}}
    const int status=std::fclose(out);std::fclose(in);std::printf("frames=%zu latency_samples=%zu maximum_bell_cut_db=%.6f\n",count,delay,maxReduction);return status?4:0;
}
