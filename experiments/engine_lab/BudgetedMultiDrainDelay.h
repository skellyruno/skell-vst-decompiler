#pragma once
#include "DrainingDelayResearch.h"
#include "WetBudgetResearch.h"
namespace skell_lab {
// Four fixed feedback banks; shortest remaining drain is faded on capacity pressure.
// Latest request wins. No allocation or history clearing in process.
class BudgetedMultiDrainDelay {
    static constexpr int count=4;
    struct Bank {
        std::vector<Frame> ring;std::size_t pos=0,valid=0,n=1,remaining=0;double delay=0;
        FractionalAllpass2 l,r;bool fractional=false,used=false;
        void start(double samples) noexcept {delay=samples;const double whole=std::floor(samples),f=samples-whole;fractional=f>=.05&&f<=.95;n=std::size_t(fractional?whole-1:std::round(samples));if(fractional){l.prepare(f);r.prepare(f);}else{l.reset();r.reset();}pos=valid=remaining=0;used=true;}
        Frame process(Frame x,double fb) noexcept {Frame y=valid>=n?ring[pos]:Frame{};if(fractional)y={l.process(y.l),r.process(y.r)};ring[pos]={std::clamp(x.l+fb*y.l,-32.,32.),std::clamp(x.r+fb*y.r,-32.,32.)};if(valid<n)++valid;if(++pos==n)pos=0;return y;}
    } banks[count];
    double fs=48000,maximum=0,current=0,feedback=.7,mix=1,repeats=1;
    std::size_t fade=2,age=0;int active=0,outgoing=-1;unsigned forced=0;WetBudget budget;
    static double smooth(double t) noexcept {return t*t*(3-2*t);}
    std::size_t life(double d)const noexcept{return std::size_t(std::ceil(d)*repeats)+128+fade;}
public:
    bool prepare(double rate,double initialSamples,double seconds=2,double fb=.7,double wet=1){
        if(!std::isfinite(rate)||rate<8000||rate>384000||!std::isfinite(seconds)||seconds<.01||seconds>4)return false;
        fs=rate;maximum=std::floor(rate*seconds);feedback=bound(fb,0,.95,.7);mix=bound(wet,0,1,1);fade=std::max<std::size_t>(2,std::size_t(std::round(fs*.025)));repeats=feedback>0?std::ceil(std::log(.001)/std::log(feedback)):1.;
        for(auto& b:banks){b.ring.assign(std::size_t(maximum)+1,{});b.used=false;}active=0;outgoing=-1;forced=0;current=bound(initialSamples,2,maximum,2);banks[active].start(current);budget.prepare(fs);return true;
    }
    double activeDelay()const noexcept{return current;}
    unsigned forcedRetirements()const noexcept{return forced;}
    unsigned liveBanks()const noexcept{unsigned n=0;for(const auto& b:banks)n+=b.used;return n;}
    Frame process(Frame x,double requested) noexcept {
        x={finite(x.l),finite(x.r)};if(banks[0].ring.empty())return x;
        const double target=bound(requested,2,maximum,current);
        if(outgoing<0&&std::abs(target-current)>.01){
            int free=-1,victim=-1;for(int i=0;i<count;++i){if(!banks[i].used){free=i;break;}if(i!=active&&(victim<0||banks[i].remaining<banks[victim].remaining))victim=i;}
            if(free>=0){outgoing=active;active=free;banks[active].start(target);current=target;age=0;}
            else if(victim>=0&&banks[victim].remaining>fade){banks[victim].remaining=fade;++forced;}
        }
        const double a=outgoing<0?1.:smooth(double(age)/double(fade-1));Frame primary{},tail{};
        for(int i=0;i<count;++i){auto& b=banks[i];if(!b.used)continue;const double feed=i==active?a:i==outgoing?1-a:0.;const auto z=b.process({feed*x.l,feed*x.r},feedback);
            const bool retiring=i!=active&&i!=outgoing;const double weight=retiring&&b.remaining<=fade?smooth(double(b.remaining-1)/double(fade-1)):1.;auto& part=retiring?tail:primary;part.l+=weight*z.l;part.r+=weight*z.r;
            if(retiring&&--b.remaining==0)b.used=false;
        }
        if(outgoing>=0&&++age==fade){banks[outgoing].remaining=life(banks[outgoing].delay);outgoing=-1;}
        const auto y=budget.process(primary,tail);
        return {x.l*(1-mix)+mix*y.l,x.r*(1-mix)+mix*y.r};
    }
};
}
