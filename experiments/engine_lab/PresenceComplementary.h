#pragma once
#include "IndependentEngines.h"
namespace skell_lab {
// Independent alternative: keep the LR4 high-band detector, but apply gain to
// a complementary first-order TPT highpass. No dry/wet all-pass cancellation.
class PresenceComplementary {
    Biquad detector[2][2];
    double state[2]{}, alpha=0, env=0, gain=1, rise=0, fall=0, smooth=0;
    double boost=1, trigger=.1, strength=0, wet=1;
public:
    void prepare(double sampleRate,double cutoffHz=2600,double boostDb=3,
                 double thresholdDb=-22,double amount=.7,double mix=1) noexcept {
        const double fs=bound(sampleRate,8000,384000,48000);
        const double fc=bound(cutoffHz,80,fs*.4,2600);
        const double t=std::tan(pi*fc/fs);alpha=t/(1+t);
        for(auto& c:detector)for(auto& b:c)b.setButterworth(fs,fc,true);
        boost=fromDb(bound(boostDb,-12,12,0));trigger=fromDb(bound(thresholdDb,-72,0,-22));
        strength=bound(amount,0,2,.7);wet=bound(mix,0,1,1);
        rise=pole(1.5,fs);fall=pole(70,fs);smooth=pole(2,fs);reset();
    }
    void reset() noexcept {
        for(auto& c:detector)for(auto& b:c)b.reset();
        state[0]=state[1]=env=0;gain=boost;
    }
    Frame process(Frame x) noexcept {
        const double v[]{finite(x.l),finite(x.r)};
        double hi[2],peak=0;
        for(int c=0;c<2;++c){
            const double d=detector[c][1].process(detector[c][0].process(v[c]));
            peak=std::max(peak,std::abs(d));
            const double delta=alpha*(v[c]-state[c]);
            const double lo=state[c]+delta;state[c]=lo+delta;
            if(std::abs(state[c])<1e-30)state[c]=0;
            hi[c]=v[c]-lo;
        }
        const double p=peak>env?rise:fall;env=p*env+(1-p)*peak;
        const double target=boost/(1+strength*std::max(0.,env/trigger-1));
        gain=smooth*gain+(1-smooth)*target;
        const double scale=wet*(gain-1);
        return {v[0]+scale*hi[0],v[1]+scale*hi[1]};
    }
};
}
