#pragma once
#include "WetBudgetResearch.h"
namespace skell_lab {
// Complementary 250 Hz split of the draining tail. High-band tail gets
// priority over low-band tail. Final linked sample ceiling, not true peak.
class BandTailBudget {
    double ceiling=1,release=0,split=0,primaryGain=1,highGain=1,lowGain=1;
    Frame low{};
    double recover(double g,double cap)const noexcept {return std::min(cap,release*g+(1-release));}
    double allowed(double p,double t)const noexcept {
        if(t>0)return std::clamp((ceiling-p)/t,0.,1.);
        if(t<0)return std::clamp((-ceiling-p)/t,0.,1.);
        return 1.;
    }
    Frame add(Frame p,Frame t,double& g)noexcept {g=recover(g,std::min(allowed(p.l,t.l),allowed(p.r,t.r)));return {p.l+g*t.l,p.r+g*t.r};}
public:
    void prepare(double fs,double ceilingDb=-1,double releaseMs=30)noexcept {fs=bound(fs,8000,384000,48000);ceiling=fromDb(bound(ceilingDb,-18,0,-1));release=pole(bound(releaseMs,1,1000,30),fs);split=std::exp(-2*pi*250/fs);reset();}
    void reset()noexcept {low={};primaryGain=highGain=lowGain=1;}
    Frame process(Frame p,Frame t)noexcept {
        p={finite(p.l),finite(p.r)};t={finite(t.l),finite(t.r)};
        low={split*low.l+(1-split)*t.l,split*low.r+(1-split)*t.r};
        if(std::abs(low.l)<1e-30)low.l=0;
        if(std::abs(low.r)<1e-30)low.r=0;
        const Frame high{t.l-low.l,t.r-low.r};
        const double peak=std::max(std::abs(p.l),std::abs(p.r));primaryGain=recover(primaryGain,peak>ceiling?ceiling/peak:1.);
        p={p.l*primaryGain,p.r*primaryGain};
        // When neither budget is active, avoid unnecessarily recombining
        // the split tail, including when its two bands cancel each other.
        if(highGain==1.&&lowGain==1.&&std::max(std::abs(p.l+t.l),std::abs(p.r+t.r))<=ceiling)return {p.l+t.l,p.r+t.r};
        return add(add(p,high,highGain),low,lowGain);
    }
};
}
