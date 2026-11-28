#pragma once
#include "IndependentEngines.h"
namespace skell_lab {
// Experimental comparator: original peak envelope and activity memory,
// immediate gain attack after that envelope, original gain release.
class LevelerSingleAttack {
    double attack=0, releaseFast=0, releaseSlow=0, memoryPole=0;
    double grRelease=0, threshold=.2, exponent=.5, makeup=1, wet=1;
    double env=0, memory=0, gain=1;
public:
    void prepare(double fs,double thresholdDb=-18,double ratio=3,double attackMs=4,
                 double releaseMs=120,double makeupDb=0,double mix=1) noexcept {
        fs=bound(fs,8000,384000,48000);
        threshold=fromDb(bound(thresholdDb,-72,0,-18));
        exponent=1-1/bound(ratio,1,20,3);makeup=fromDb(bound(makeupDb,-18,18,0));wet=bound(mix,0,1,1);
        const double a=bound(attackMs,.1,100,4),r=bound(releaseMs,5,3000,120);
        attack=pole(a,fs);releaseFast=pole(r,fs);releaseSlow=pole(3*r,fs);memoryPole=pole(2*r,fs);grRelease=pole(r,fs);reset();
    }
    void reset() noexcept {env=memory=0;gain=1;}
    Frame process(Frame x) noexcept {
        x={finite(x.l),finite(x.r)};
        const double p=std::max(std::abs(x.l),std::abs(x.r));
        memory=memoryPole*memory+(1-memoryPole)*p;
        const double activity=memory/(memory+threshold+1e-18);
        const double fall=releaseFast*(1-activity)+releaseSlow*activity;
        const double coeff=p>env?attack:fall;
        env=coeff*env+(1-coeff)*p;
        const double target=env>threshold&&exponent>0?std::pow(threshold/env,exponent):1;
        gain=target<gain?target:grRelease*gain+(1-grRelease)*target;
        const double g=makeup*gain;
        return {x.l*(1-wet+wet*g),x.r*(1-wet+wet*g)};
    }
};
}
