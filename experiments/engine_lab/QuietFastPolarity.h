#pragma once
#include "BoundedPeakResearch.h"
namespace skell_lab {
// Separate positive/negative bounds and exact exponential release-deficit bound.
class QuietFastPolarity {
    using K=ReconstructionGuard;
    K::Kernel h{};std::array<Frame,2*K::count> ring{};std::array<double,K::count> cap{},rise{};
    int head=0;double gain=1,ceiling=1,release=0,quietThreshold=0;
    unsigned long long quiet=0,total=0;
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
        // m_j=max_{k>=j}g_k is nonincreasing. 0<=m_j-g_j<=1-r^(last-j).
        // Upper reconstruction uses positive prefix and negative residual only;
        // lower reconstruction uses negative prefix and positive residual only.
        return std::min(safe(a.pos,a.hi,a.en),safe(a.neg,-a.lo,a.ep));
    }
public:
    static constexpr int latency=K::latency;
    void prepare(double fs,double ceilingDb=-1,double releaseMs=60) noexcept {
        fs=bound(fs,8000,384000,48000);ceiling=fromDb(bound(ceilingDb,-18,0,-1));release=pole(bound(releaseMs,1,1000,60),fs);
        K old;old.prepare(fs,ceilingDb,releaseMs);h=old.kernel();double maxSum=1;for(const auto& phase:h){double sum=0;for(double k:phase)sum+=std::abs(k);maxSum=std::max(maxSum,sum);}quietThreshold=ceiling/(maxSum*(1+1e-12));for(int j=0;j<K::count;++j)rise[j]=-std::expm1((K::count-1-j)*std::log(release));reset();
    }
    const K::Kernel& kernel() const noexcept{return h;}
    void reset() noexcept{ring.fill({0,0});cap.fill(1);head=0;gain=1;quiet=total=0;}
    unsigned long long skippedWindows()const noexcept{return quiet;}
    unsigned long long totalWindows()const noexcept{return total;}
    Frame process(Frame x) noexcept {
        ring[head]=ring[head+K::count]={finite(x.l),finite(x.r)};cap[head]=1;
        const Frame* v=ring.data()+head+1;double peak=0;for(int j=0;j<K::count;++j)peak=std::max({peak,std::abs(v[j].l),std::abs(v[j].r)});++total;
        double g=1.;if(peak<=quietThreshold)++quiet;else {const auto c=v[K::radius];const double p=std::max(std::abs(c.l),std::abs(c.r));g=p>ceiling?ceiling/p:1.;
        for(int i=1;i<4;++i){Acc l{},r{};for(int j=0;j<K::count;++j){add(l,h[i][j]*v[j].l,rise[j]);add(r,h[i][j]*v[j].r,rise[j]);}g=std::min({g,limit(l),limit(r)});}}
        for(auto& q:cap)q=std::min(q,g);
        const int oldest=(head+1)%K::count;gain=std::min(cap[oldest],release*gain+(1-release));const auto y=ring[oldest];head=oldest;return {y.l*gain,y.r*gain};
    }
};
}
