#pragma once
#include "BoundedPeakResearch.h"
#include <limits>
namespace skell_lab {
// Precompute release poles at input time, retain alongside delayed samples.
// Each reconstruction window can use its exact scheduled future recovery
// deficits, rather than assuming the fastest pole across the whole window.
class ScheduledRecoveryGuard {
    using K=ReconstructionGuard;
    K::Kernel h{};std::array<Frame,2*K::count> ring{};std::array<double,K::count> cap{},rise{};
    std::array<double,2*K::count> poles{};
    int head=0;double gain=1,ceiling=1,release=0,quietThreshold=0;
    unsigned long long quiet=0,total=0;
    double slowRelease=0,lowPole=0,energyPole=0,lowL=0,lowR=0,lowEnergy=0,fullEnergy=0;
    struct Acc {double pos=0,neg=0,s=0,hi=0,lo=0,ep=0,en=0;};
    static void add(Acc& a,double w,double r) noexcept {
        const double p=std::max(0.,w),n=std::max(0.,-w);
        a.pos+=p;a.neg+=n;a.s+=w;a.hi=std::max(a.hi,a.s);a.lo=std::min(a.lo,a.s);a.ep+=r*p;a.en+=r*n;
    }
    double safe(double lobe,double prefix,double err) const noexcept {
        double g=lobe>ceiling?ceiling/lobe:1.;
        if(err<ceiling){const double avail=ceiling-err;g=std::max(g,prefix>avail?avail/prefix:1.);}
        return g;
    }
    double limit(const Acc& a) const noexcept {
        // m_j=max_{k>=j}g_k is nonincreasing. Deficits are bounded by
        // 1-product of the scheduled poles at j+1 through last.
        // Upper reconstruction uses positive prefix and negative residual only;
        // lower reconstruction uses negative prefix and positive residual only.
        return std::min(safe(a.pos,a.hi,a.en),safe(a.neg,-a.lo,a.ep));
    }
public:
    static constexpr int latency=K::latency;
    void prepare(double fs,double ceilingDb=-1,double releaseMs=1) noexcept {
        fs=bound(fs,8000,384000,48000);ceiling=fromDb(bound(ceilingDb,-18,0,-1));release=pole(bound(releaseMs,1,1000,60),fs);
        slowRelease=std::max(release,pole(60,fs));lowPole=std::exp(-2*pi*120/fs);energyPole=pole(20,fs);
        K old;old.prepare(fs,ceilingDb,releaseMs);h=old.kernel();double maxSum=1;for(const auto& phase:h){double sum=0;for(double k:phase)sum+=std::abs(k);maxSum=std::max(maxSum,sum);}quietThreshold=ceiling/(maxSum*(1+1e-12));reset();
    }
    const K::Kernel& kernel() const noexcept{return h;}
    void reset() noexcept{ring.fill({0,0});cap.fill(1);poles.fill(release);head=0;gain=1;quiet=total=0;lowL=lowR=lowEnergy=fullEnergy=0;}
    unsigned long long skippedWindows()const noexcept{return quiet;}
    unsigned long long totalWindows()const noexcept{return total;}
    Frame process(Frame x) noexcept {
        x={finite(x.l),finite(x.r)};
        // Same detector law, computed in input order and stored with its sample.
        // Scale detector input to avoid squaring unbounded finite samples.
        const double l=std::clamp(x.l,-32.,32.),r=std::clamp(x.r,-32.,32.);
        lowL=lowPole*lowL+(1-lowPole)*l;lowR=lowPole*lowR+(1-lowPole)*r;
        lowEnergy=energyPole*lowEnergy+(1-energyPole)*(lowL*lowL+lowR*lowR);
        fullEnergy=energyPole*fullEnergy+(1-energyPole)*(l*l+r*r);
        const double blend=std::clamp((lowEnergy/(fullEnergy+1e-20)-.15)/.65,0.,1.);
        const double actual=std::clamp(release+(slowRelease-release)*blend,release,slowRelease);
        poles[head]=poles[head+K::count]=actual;
        ring[head]=ring[head+K::count]=x;cap[head]=1;
        const Frame* v=ring.data()+head+1;double peak=0;for(int j=0;j<K::count;++j)peak=std::max({peak,std::abs(v[j].l),std::abs(v[j].r)});++total;
        double g=1.;if(peak<=quietThreshold)++quiet;else {const auto c=v[K::radius];const double p=std::max(std::abs(c.l),std::abs(c.r));g=p>ceiling?ceiling/p:1.;
        // In exact arithmetic the suffix recurrence bounds 1-product(R).
        // Round the small deficit upward by a fixed double-precision margin.
        rise[K::count-1]=0.;const double* schedule=poles.data()+head+1;
        for(int j=K::count-2;j>=0;--j){const double r=schedule[j+1];rise[j]=std::min(1.,(1-r)+r*rise[j+1]+8*std::numeric_limits<double>::epsilon());}
        for(int i=1;i<4;++i){Acc l{},r{};for(int j=0;j<K::count;++j){add(l,h[i][j]*v[j].l,rise[j]);add(r,h[i][j]*v[j].r,rise[j]);}g=std::min({g,limit(l),limit(r)});}}
        for(auto& q:cap)q=std::min(q,g);
        const int oldest=(head+1)%K::count;const auto y=ring[oldest];
        gain=std::min(cap[oldest],poles[oldest]*gain+(1-poles[oldest]));head=oldest;return {y.l*gain,y.r*gain};
    }
};
}
