#pragma once
#include "IndependentEngines.h"
namespace skell_lab {
// Experimental fixed-rate crest interval estimator. Not a pitch detector.
class RegularCrestHold {
    double fs=48000,attack=0,fast=0,slow=0,memPole=0,release=0;
    double env=0,mem=0,gain=1,prev=0,prev2=0,lastPeak=0;
    unsigned elapsed=0,remaining=0,hold=0,minHold=0,maxHold=0,lastInterval=0;
public:
    void prepare(double rate,double attackMs=7.83) noexcept {
        fs=bound(rate,8000,384000,48000);attack=pole(bound(attackMs,.1,100,4),fs);
        fast=pole(120,fs);slow=pole(360,fs);memPole=pole(240,fs);release=pole(120,fs);
        minHold=unsigned(std::round(fs*.002));maxHold=unsigned(std::round(fs*.032));reset();
    }
    void reset() noexcept {env=mem=prev=prev2=lastPeak=0;gain=1;elapsed=remaining=lastInterval=0;hold=minHold;}
    unsigned holdSamples() const noexcept{return hold;}
    Frame process(Frame x) noexcept {
        x={finite(x.l),finite(x.r)};const double p=std::max(std::abs(x.l),std::abs(x.r));
        const double threshold=fromDb(-18);
        if(elapsed<maxHold+1)++elapsed;
        if(prev>prev2&&prev>=p&&prev>threshold&&prev>=.8*lastPeak){
            if(lastPeak>0&&elapsed<=maxHold){
                // Require two similar intervals before extending the hold.
                const bool stable=lastInterval>0&&std::abs(double(elapsed)-lastInterval)<=.2*lastInterval;
                hold=stable?std::clamp(unsigned(std::round(1.15*elapsed)),minHold,maxHold):minHold;
                if(!stable)remaining=std::min(remaining,minHold);
                lastInterval=elapsed;
            }
            lastPeak=prev;elapsed=0;
        }
        if(elapsed>maxHold){lastPeak=0;lastInterval=0;hold=minHold;remaining=std::min(remaining,minHold);}
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
}
