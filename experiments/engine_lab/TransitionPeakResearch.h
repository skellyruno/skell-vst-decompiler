#pragma once
#include "AdaptiveResearch.h"
#include <array>
#include <vector>
namespace skell_lab {
// Conservative linked ceiling for a declared finite 4-phase reconstruction kernel.
// 16 samples latency; no allocation in process. Not an ITU true-peak meter.
class ReconstructionGuard {
public:
    static constexpr int radius=8, count=2*radius+1, latency=2*radius;
    using Kernel=std::array<std::array<double,count>,4>;
private:
    Kernel h{};std::array<Frame,count> ring{};std::array<double,count> cap{};
    int head=0;double gain=1,ceiling=1,release=0;bool conservative=true;
public:
    void prepare(double fs,double ceilingDb=-1,double releaseMs=60,bool boundMode=true) noexcept {
        fs=bound(fs,8000,384000,48000);ceiling=fromDb(bound(ceilingDb,-18,0,-1));release=pole(bound(releaseMs,1,1000,60),fs);conservative=boundMode;
        for(int p=0;p<4;++p){double sum=0;for(int j=0;j<count;++j){const double t=j-radius-p*.25;const double w=.42+.5*std::cos(pi*t/(radius+1))+.08*std::cos(2*pi*t/(radius+1));h[p][j]=p==0?(j==radius?1.:0.):(std::sin(pi*t)/(pi*t))*w;sum+=h[p][j];}for(auto& v:h[p])v/=sum;}
        reset();
    }
    const Kernel& kernel() const noexcept{return h;}
    void reset() noexcept {ring.fill({0,0});cap.fill(1);head=0;gain=1;}
    Frame process(Frame x) noexcept {
        ring[head]={finite(x.l),finite(x.r)};cap[head]=1;
        double peak=0;for(const auto& phase:h){double l=0,r=0;int i=(head+1)%count;for(double k:phase){const auto v=ring[i];l+=conservative?std::abs(k*v.l):k*v.l;r+=conservative?std::abs(k*v.r):k*v.r;if(++i==count)i=0;}peak=std::max({peak,std::abs(l),std::abs(r)});}
        const double limit=peak>ceiling?ceiling/peak:1.;for(auto& v:cap)v=std::min(v,limit);
        const int oldest=(head+1)%count;gain=std::min(cap[oldest],release*gain+(1-release));const auto v=ring[oldest];head=oldest;return {v.l*gain,v.r*gain};
    }
};
// Two preallocated, independent fixed-coefficient feedback loops. A new loop
// warms before its output crossfade. Old history is retired, not transferred.
class TransitionDelay2 {
    struct Bank {
        std::vector<Frame> ring;std::size_t pos=0,valid=0,n=1;
        FractionalAllpass2 l,r;bool fractional=false;
        void start(double samples) noexcept {const double whole=std::floor(samples),f=samples-whole;fractional=f>=.05&&f<=.95;n=std::size_t(fractional?whole-1:std::round(samples));if(fractional){l.prepare(f);r.prepare(f);}else{l.reset();r.reset();}pos=valid=0;}
        Frame process(Frame x,double fb) noexcept {Frame y=valid>=n?ring[pos]:Frame{0,0};if(fractional)y={l.process(y.l),r.process(y.r)};ring[pos]={std::clamp(x.l+fb*y.l,-32.,32.),std::clamp(x.r+fb*y.r,-32.,32.)};if(valid<n)++valid;if(++pos==n)pos=0;return y;}
    } banks[2];
    double fs=48000,maximum=0,current=0,target=0,pending=0,feedback=.7,mix=1;
    std::size_t warm=0,fade=0,age=0;int active=0;bool transitioning=false;
public:
    bool prepare(double rate,double initialSamples,double seconds=2,double fb=.7,double wet=1){
        if(!std::isfinite(rate)||rate<8000||rate>384000||!std::isfinite(seconds)||seconds<.01||seconds>4)return false;
        fs=rate;maximum=std::floor(rate*seconds);for(auto& b:banks)b.ring.assign(std::size_t(maximum)+1,{0,0});feedback=bound(fb,0,.95,.7);mix=bound(wet,0,1,1);fade=std::max<std::size_t>(2,std::size_t(std::round(fs*.025)));current=target=pending=bound(initialSamples,2,maximum,2);active=0;transitioning=false;banks[0].start(current);return true;
    }
    double activeDelay()const noexcept{return current;}
    bool busy()const noexcept{return transitioning;}
    Frame process(Frame x,double requested) noexcept {
        x={finite(x.l),finite(x.r)};if(banks[0].ring.empty())return x;
        pending=bound(requested,2,maximum,current);
        if(!transitioning&&std::abs(pending-current)>.01){target=pending;banks[1-active].start(target);warm=std::size_t(std::ceil(target))+128;age=0;transitioning=true;}
        Frame y=banks[active].process(x,feedback);
        if(transitioning){const auto z=banks[1-active].process(x,feedback);if(warm)--warm;else{const double t=double(age)/double(fade-1),a=t*t*(3-2*t);y={y.l+a*(z.l-y.l),y.r+a*(z.r-y.r)};if(++age==fade){active=1-active;current=target;transitioning=false;}}}
        return {x.l*(1-mix)+mix*y.l,x.r*(1-mix)+mix*y.r};
    }
};
}
