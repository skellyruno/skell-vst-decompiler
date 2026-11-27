#pragma once
#include "IndependentEngines.h"
namespace skell_lab {
// Experimental fixed-rate crest interval estimator. Not a pitch detector.
class AdaptiveHold {
    double fs=48000,attack=0,fast=0,slow=0,memPole=0,release=0;
    double env=0,mem=0,gain=1,prev=0,prev2=0,lastPeak=0;
    unsigned elapsed=0,remaining=0,hold=0,minHold=0,maxHold=0;
public:
    void prepare(double rate,double attackMs=7.83) noexcept {
        fs=bound(rate,8000,384000,48000);attack=pole(bound(attackMs,.1,100,4),fs);
        fast=pole(120,fs);slow=pole(360,fs);memPole=pole(240,fs);release=pole(120,fs);
        minHold=unsigned(std::round(fs*.002));maxHold=unsigned(std::round(fs*.032));reset();
    }
    void reset() noexcept {env=mem=prev=prev2=lastPeak=0;gain=1;elapsed=remaining=0;hold=minHold;}
    unsigned holdSamples() const noexcept{return hold;}
    Frame process(Frame x) noexcept {
        x={finite(x.l),finite(x.r)};const double p=std::max(std::abs(x.l),std::abs(x.r));
        const double threshold=fromDb(-18);
        if(elapsed<maxHold+1)++elapsed;
        if(prev>prev2&&prev>=p&&prev>threshold&&prev>=.8*lastPeak){
            if(lastPeak>0&&elapsed<=maxHold)hold=std::clamp(unsigned(std::round(1.15*elapsed)),minHold,maxHold);
            lastPeak=prev;elapsed=0;
        }
        if(elapsed>maxHold){lastPeak=0;hold=minHold;}
        prev2=prev;prev=p;
        mem=memPole*mem+(1-memPole)*p;const double activity=mem/(mem+threshold+1e-18);
        const double k=p>env?attack:fast*(1-activity)+slow*activity;env=k*env+(1-k)*p;
        const double target=env>threshold?std::pow(threshold/env,.75):1;
        if(target<gain){gain=target;remaining=hold;}
        else if(remaining)--remaining;
        else gain=release*gain+(1-release)*target;
        return {x.l*gain,x.r*gain};
    }
};
// Fixed second-order Thiran allpass with total delay 1+fraction. No automation.
class FractionalAllpass2 {
    double a=0,b=0,x1=0,x2=0,y1=0,y2=0;
public:
    bool prepare(double f) noexcept {
        if(!std::isfinite(f)||f<.05||f>.95)return false;
        const double d=1+f;a=-2*(d-2)/(d+1);b=(d-2)*(d-1)/((d+1)*(d+2));reset();return true;
    }
    void reset() noexcept{x1=x2=y1=y2=0;}
    double process(double x) noexcept {
        x=finite(x);const double y=b*x+a*x1+x2-a*y1-b*y2;
        x2=x1;x1=x;y2=y1;y1=std::abs(y)<1e-30?0:y;return y;
    }
};
// Linked instantaneous sample ceiling with exponential release; not true-peak limiting.
class LinkedSampleGuard {
    double gain=1,ceiling=.891250938,release=0;
public:
    void prepare(double fs,double ceilingDb=-1,double releaseMs=60) noexcept {
        fs=bound(fs,8000,384000,48000);ceiling=fromDb(bound(ceilingDb,-18,0,-1));release=pole(bound(releaseMs,1,1000,60),fs);reset();
    }
    void reset() noexcept{gain=1;}
    double currentGain() const noexcept{return gain;}
    Frame process(Frame x) noexcept {
        x={finite(x.l),finite(x.r)};const double peak=std::max(std::abs(x.l),std::abs(x.r));
        const double want=peak>ceiling?ceiling/peak:1;
        gain=std::min(want,release*gain+(1-release));
        return {x.l*gain,x.r*gain};
    }
};
}
