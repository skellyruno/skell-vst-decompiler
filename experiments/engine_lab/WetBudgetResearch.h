#pragma once
#include "IndependentEngines.h"
namespace skell_lab {
// Stereo-linked sample ceiling for a primary wet path plus draining tails.
// Prefer preserving primary echoes. No intersample guarantee; no dry-path change.
class WetBudget {
    double ceiling=1,release=0,primaryGain=1,tailGain=1;
    double recover(double g,double cap)const noexcept {return std::min(cap,release*g+(1-release));}
    double allowed(double p,double t)const noexcept {
        if(t>0)return std::clamp((ceiling-p)/t,0.,1.);
        if(t<0)return std::clamp((-ceiling-p)/t,0.,1.);
        return 1.;
    }
public:
    void prepare(double fs,double ceilingDb=-1,double releaseMs=30)noexcept{ceiling=fromDb(bound(ceilingDb,-18,0,-1));release=pole(bound(releaseMs,1,1000,30),bound(fs,8000,384000,48000));reset();}
    void reset()noexcept{primaryGain=tailGain=1;}
    Frame process(Frame p,Frame t)noexcept {
        p={finite(p.l),finite(p.r)};t={finite(t.l),finite(t.r)};
        const double peak=std::max(std::abs(p.l),std::abs(p.r));primaryGain=recover(primaryGain,peak>ceiling?ceiling/peak:1.);
        p={p.l*primaryGain,p.r*primaryGain};tailGain=recover(tailGain,std::min(allowed(p.l,t.l),allowed(p.r,t.r)));
        return {p.l+tailGain*t.l,p.r+tailGain*t.r};
    }
};
}
