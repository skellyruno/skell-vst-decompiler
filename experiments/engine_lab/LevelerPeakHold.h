#pragma once
#include "IndependentEngines.h"
namespace skell_lab {
// Experimental crest hold after the detector: decouple rapid downward gain
// changes from gain ripple between low-frequency crests. No lookahead.
class LevelerPeakHold {
    double attack=0,releaseFast=0,releaseSlow=0,memoryPole=0,grRelease=0;
    double threshold=.2,exponent=.75,wet=1,env=0,memory=0,gain=1;
    unsigned hold=0,remaining=0;
public:
    void prepare(double fs,double attackMs=4,double holdMs=12,double mix=1) noexcept {
        fs=bound(fs,8000,384000,48000);attack=pole(bound(attackMs,.1,100,4),fs);
        threshold=fromDb(-18);releaseFast=pole(120,fs);releaseSlow=pole(360,fs);
        memoryPole=pole(240,fs);grRelease=pole(120,fs);wet=bound(mix,0,1,1);
        hold=unsigned(std::round(fs*.001*bound(holdMs,0,50,12)));reset();
    }
    void reset() noexcept {env=memory=0;gain=1;remaining=0;}
    Frame process(Frame x) noexcept {
        x={finite(x.l),finite(x.r)};const double p=std::max(std::abs(x.l),std::abs(x.r));
        memory=memoryPole*memory+(1-memoryPole)*p;
        const double activity=memory/(memory+threshold+1e-18);
        const double fall=releaseFast*(1-activity)+releaseSlow*activity;
        const double coeff=p>env?attack:fall;env=coeff*env+(1-coeff)*p;
        const double target=env>threshold?std::pow(threshold/env,exponent):1;
        if(target<gain){gain=target;remaining=hold;}
        else if(remaining) --remaining;
        else gain=grRelease*gain+(1-grRelease)*target;
        const double g=1-wet+wet*gain;return {x.l*g,x.r*g};
    }
};
}
