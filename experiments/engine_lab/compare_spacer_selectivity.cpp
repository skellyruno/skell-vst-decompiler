#include "Spacer3.h"
#include "SpacerSelective.h"
#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <chrono>
#include <limits>
#include <cstring>
using namespace skell_lab;
template<class T> auto left(T v){return v[0];}
template<> auto left(Spacer3::Frame v){return v.l;}
template<class T> auto right(T v){return v[1];}
template<> auto right(Spacer3::Frame v){return v.r;}
template<class T> void render(int fs,int hz){
    T p; typename T::Settings s;s.attackMs=5;s.releaseMs=50;s.depth=.85;p.prepare(fs,s);
    constexpr double pi=3.141592653589793;
    for(int i=0;i<2*fs;++i){double t=double(i)/fs;
        float x=float((std::sin(2*pi*100*t)+std::sin(2*pi*1000*t)+std::sin(2*pi*9000*t))/6.);
        auto v=p.tick(x,x,float(.5*std::sin(2*pi*hz*t)),0.f);
        if(i>=fs){float row[]={x,x,left(v),right(v)};if(std::fwrite(row,sizeof(float),4,stdout)!=4)std::exit(1);}
    }
}
int main(int argc,char** argv){
    if(argc==3){int fs=std::atoi(argv[2]);if(fs<22000||fs>192000)return 2;
        for(int hz:{100,1000,9000}){if(std::strcmp(argv[1],"baseline")==0)render<Spacer3>(fs,hz);else if(std::strcmp(argv[1],"candidate")==0)render<SpacerSelective>(fs,hz);else return 2;}return 0;}
    for(int fs:{44100,48000,96000,192000})for(bool ms:{false,true}){
        SpacerSelective p;SpacerSelective::Settings s;s.depth=0;s.midSide=ms;p.prepare(fs,s);assert(p.bandCount()>10);
        for(int i=0;i<fs/4;++i){float l=float(.4*std::sin(i*.13)),r=float(.4*std::cos(i*.03));auto v=p.tick(l,r,.9f,-.9f);assert(v[0]==l&&v[1]==r);}
        s.depth=.85;p.prepare(fs,s);auto v=p.tick(.5f,0,0,0);assert(v[0]==.5f&&v[1]==0);
        v=p.tick(std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity(),0,0);assert(std::isfinite(v[0])&&std::isfinite(v[1]));
        p.reset();for(int i=0;i<fs;++i){float x=float(.3*std::sin(i*.13));v=p.tick(x,ms?x:0,i<fs/2?x:0,ms&&i<fs/2?x:0);assert(std::isfinite(v[0])&&std::isfinite(v[1]));if(ms)assert(v[0]==v[1]);else assert(v[1]==0);}
    }
    auto bench=[](auto p){p.prepare(48000,{});double sum=0;auto t=std::chrono::steady_clock::now();for(int i=0;i<480000;++i){auto v=p.tick(float(i%97)*.001f,float(i%53)*.001f,float(i%127)*.003f,float(i%41)*.001f);sum+=left(v);}auto d=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count()/10000.;std::printf("%.4f us/48 stereo frames checksum %.8f\n",d,sum);};
    bench(Spacer3{});bench(SpacerSelective{});
}
