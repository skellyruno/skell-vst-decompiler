#pragma once
#include "TransitionPeakResearch.h"
namespace skell_lab {
// Guaranteed for the same finite 4-phase reconstruction kernel as ReconstructionGuard.
// Three independent safe bounds: absolute sum, signed lobe, and release-constrained prefix.
// The latter two account for cancellation without assuming equal gain across a window.
class BoundedPeakGuard {
    using K=ReconstructionGuard;
    K::Kernel h{};std::array<Frame,2*K::count> ring{};std::array<double,K::count> cap{};
    int head=0,mode=2;double gain=1,ceiling=1,release=0;
    struct Accumulator {double positive=0,negative=0,prefix=0,maxPrefix=0,riseError=0;};
    template<int Mode> static void add(Accumulator& a,double w,int j) noexcept {
        a.positive+=std::max(0.,w);a.negative+=std::max(0.,-w);
        if constexpr(Mode==2){a.prefix+=w;a.maxPrefix=std::max(a.maxPrefix,std::abs(a.prefix));a.riseError+=(K::count-1-j)*std::abs(w);}
    }
    template<int Mode> double capFor(const Accumulator& a) const noexcept {
        // For 0<=g_j<=G, positive and negative sums separately bound either polarity.
        const double magnitude=Mode==0?a.positive+a.negative:std::max(a.positive,a.negative);
        double safe=magnitude>ceiling?ceiling/magnitude:1.;
        if constexpr(Mode==2){
            // m_j=max(g_j,...,g_last) is nonincreasing, <=G. Its weighted sum
            // is bounded by G*max(abs(prefix sums)). Since g_{j+1}-g_j<=1-release,
            // |sum(w_j*(g_j-m_j))| <= (1-release)*sum((last-j)*abs(w_j)).
            const double residual=(1-release)*a.riseError;
            if(residual<ceiling){const double available=ceiling-residual;const double prefixCap=a.maxPrefix>available?available/a.maxPrefix:1.;safe=std::max(safe,prefixCap);}
        }
        return safe;
    }
    template<int Mode> double limitForWindow() const noexcept {
        // Phase zero is the exact center sample; lobe cap dominates its prefix cap.
        // Mirrored ring gives a contiguous window, avoiding wrap in the hot loop.
        const Frame* window=ring.data()+head+1;const auto center=window[K::radius];
        const double peak=std::max(std::abs(center.l),std::abs(center.r));double limit=peak>ceiling?ceiling/peak:1.;
        for(int p=1;p<4;++p){Accumulator l{},r{};for(int j=0;j<K::count;++j){add<Mode>(l,h[p][j]*window[j].l,j);add<Mode>(r,h[p][j]*window[j].r,j);}limit=std::min({limit,capFor<Mode>(l),capFor<Mode>(r)});}
        return limit;
    }
public:
    static constexpr int latency=K::latency;
    void prepare(double fs,double ceilingDb=-1,double releaseMs=60,int boundMode=2) noexcept {
        fs=bound(fs,8000,384000,48000);ceiling=fromDb(bound(ceilingDb,-18,0,-1));release=pole(bound(releaseMs,1,1000,60),fs);mode=std::clamp(boundMode,0,2);K original;original.prepare(fs,ceilingDb,releaseMs);h=original.kernel();reset();
    }
    const K::Kernel& kernel()const noexcept{return h;}
    void reset() noexcept{ring.fill({0,0});cap.fill(1);head=0;gain=1;}
    Frame process(Frame x) noexcept{
        ring[head]=ring[head+K::count]={finite(x.l),finite(x.r)};cap[head]=1;
        const double limit=mode==0?limitForWindow<0>():mode==1?limitForWindow<1>():limitForWindow<2>();
        for(auto& v:cap)v=std::min(v,limit);
        const int oldest=(head+1)%K::count;gain=std::min(cap[oldest],release*gain+(1-release));const auto v=ring[oldest];head=oldest;return {v.l*gain,v.r*gain};
    }
};
}
