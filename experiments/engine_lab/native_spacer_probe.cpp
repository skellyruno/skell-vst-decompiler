#include "Spacer3.h"
#include <cstdio>
int main() {
    constexpr int fs=48000;
    constexpr double pi=3.141592653589793;
    for(int hz:{100,1000,9000}){
        skell_lab::Spacer3 p;
        skell_lab::Spacer3::Settings s;s.attackMs=5;s.releaseMs=50;s.depth=.85;p.prepare(fs,s);
        for(int i=0;i<2*fs;++i){
            double t=double(i)/fs;
            float x=float((std::sin(2*pi*100*t)+std::sin(2*pi*1000*t)+std::sin(2*pi*9000*t))/6.);
            auto out=p.tick(x,x,float(.5*std::sin(2*pi*hz*t)),0.f);
            if(i>=fs){float row[]={x,x,out.l,out.r};if(std::fwrite(row,sizeof(float),4,stdout)!=4)return 1;}
        }
    }
}
