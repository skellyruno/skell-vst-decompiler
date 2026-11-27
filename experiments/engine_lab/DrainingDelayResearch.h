#pragma once
#include "TransitionPeakResearch.h"
namespace skell_lab {
// Experimental input-routed transition: old loop drains without new input;
// new loop starts immediately. Old and new wet outputs sum (not peak safe).
// Two banks only, so later requests are coalesced until the old bank retires.
class DrainingDelay {
    struct Bank {
        std::vector<Frame> ring;std::size_t pos=0,valid=0,n=1;
        FractionalAllpass2 l,r;bool fractional=false;
        void start(double samples) noexcept {const double whole=std::floor(samples),f=samples-whole;fractional=f>=.05&&f<=.95;n=std::size_t(fractional?whole-1:std::round(samples));if(fractional){l.prepare(f);r.prepare(f);}else{l.reset();r.reset();}pos=valid=0;}
        Frame process(Frame x,double fb) noexcept{Frame y=valid>=n?ring[pos]:Frame{0,0};if(fractional)y={l.process(y.l),r.process(y.r)};ring[pos]={std::clamp(x.l+fb*y.l,-32.,32.),std::clamp(x.r+fb*y.r,-32.,32.)};if(valid<n)++valid;if(++pos==n)pos=0;return y;}
    } banks[2];
    double fs=48000,maximum=0,current=0,oldDelay=0,feedback=.7,mix=1;
    std::size_t fade=2,age=0,drain=0,drainAge=0;int active=0;bool draining=false;
public:
    bool prepare(double rate,double initialSamples,double seconds=2,double fb=.7,double wet=1){
        if(!std::isfinite(rate)||rate<8000||rate>384000||!std::isfinite(seconds)||seconds<.01||seconds>4)return false;
        fs=rate;maximum=std::floor(rate*seconds);for(auto& b:banks)b.ring.assign(std::size_t(maximum)+1,{0,0});feedback=bound(fb,0,.95,.7);mix=bound(wet,0,1,1);fade=std::max<std::size_t>(2,std::size_t(std::round(fs*.025)));current=oldDelay=bound(initialSamples,2,maximum,2);active=0;draining=false;banks[0].start(current);return true;
    }
    double activeDelay()const noexcept{return current;}
    bool busy()const noexcept{return draining;}
    // Valid tempo mapping, no DAW transport coupling; supported beat lengths are bounded.
    double tempoSamples(double bpm,double beats) const noexcept{return bound(fs*60/bound(bpm,20,400,120)*bound(beats,.125,4,1),2,maximum,2);}
    Frame process(Frame x,double requested) noexcept{
        x={finite(x.l),finite(x.r)};if(banks[0].ring.empty())return x;
        const double target=bound(requested,2,maximum,current);
        if(!draining&&std::abs(target-current)>.01){oldDelay=current;current=target;active=1-active;banks[active].start(current);age=drainAge=0;draining=true;
            // Nominal 60dB recurrence decay, not a hard amplitude bound for allpass phase.
            const double repeats=feedback>0?std::ceil(std::log(.001)/std::log(feedback)):1.;
            drain=std::size_t(std::ceil(oldDelay)*std::max(1.,repeats))+128+fade;
        }
        Frame y{};
        if(draining){
            double a=1.;if(age<fade){const double t=double(age)/double(fade-1);a=t*t*(3-2*t);++age;}
            const auto next=banks[active].process({a*x.l,a*x.r},feedback);const auto old=banks[1-active].process({(1-a)*x.l,(1-a)*x.r},feedback);
            double tail=1.;if(age>=fade){if(drainAge+fade>=drain){const double t=std::clamp(double(drain-1-drainAge)/double(fade-1),0.,1.);tail=t*t*(3-2*t);}if(++drainAge>=drain)draining=false;}
            y={next.l+tail*old.l,next.r+tail*old.r};
        }else y=banks[active].process(x,feedback);
        return {x.l*(1-mix)+mix*y.l,x.r*(1-mix)+mix*y.r};
    }
};
}
