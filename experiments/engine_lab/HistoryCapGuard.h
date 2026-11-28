#pragma once
#include "BoundedPeakResearch.h"
#include <limits>
#include "PreparedPairBound.h"
namespace skell_lab {
// Precompute release poles at input time, retain alongside delayed samples.
// Each reconstruction window can use its exact scheduled future recovery
// deficits, rather than assuming the fastest pole across the whole window.
class HistoryCapGuard {
    using K=ReconstructionGuard;
    K::Kernel h{};std::array<Frame,2*K::count> ring{};std::array<double,K::count> cap{},rise{};
    std::array<double,2*K::count> poles{};
    int head=0,maxIndex=0;double windowPeak=0;std::array<double,K::count> magnitudes{};double gain=1,ceiling=1,release=0,quietThreshold=0;
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
    // Existing caps and already emitted gain are upper bounds on future gain.
    // For a pivot G0, w>0 with U<=G0 contributes a fixed upper bound w*U;
    // the rest contributes w*G. Ignore negative weights for this extra bound.
    double historyCap(const std::array<double,K::count>& w,const std::array<double,K::count>& upper,double pivot,int sign) const noexcept {
        double constant=0.,slope=0.,scale=0.;
        for(int j=0;j<K::count;++j){const double a=std::max(0.,sign*w[j]);scale+=a;if(upper[j]<=pivot)constant+=a*upper[j];else slope+=a;}
        const double available=ceiling-constant-256*std::numeric_limits<double>::epsilon()*scale;
        return available>0.? (slope>available?available/slope:1.):0.;
    }
public:
    static constexpr int latency=K::latency;
    void prepare(double fs,double ceilingDb=-1,double releaseMs=1) noexcept {
        fs=bound(fs,8000,384000,48000);ceiling=fromDb(bound(ceilingDb,-18,0,-1));release=pole(bound(releaseMs,1,1000,60),fs);
        slowRelease=std::max(release,pole(60,fs));lowPole=std::exp(-2*pi*120/fs);energyPole=pole(20,fs);
        K old;old.prepare(fs,ceilingDb,releaseMs);h=old.kernel();double maxSum=1;for(const auto& phase:h){double sum=0;for(double k:phase)sum+=std::abs(k);maxSum=std::max(maxSum,sum);}quietThreshold=ceiling/(maxSum*(1+1e-12));reset();
    }
    const K::Kernel& kernel() const noexcept{return h;}
    void reset() noexcept{ring.fill({0,0});cap.fill(1);poles.fill(release);head=maxIndex=0;windowPeak=0;magnitudes.fill(0);gain=1;quiet=total=0;lowL=lowR=lowEnergy=fullEnergy=0;}
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
        const Frame* v=ring.data()+head+1;
        // Cache the maximum until the sample holding it is overwritten.
        magnitudes[head]=std::max(std::abs(x.l),std::abs(x.r));
        if(magnitudes[head]>=windowPeak){windowPeak=magnitudes[head];maxIndex=head;}
        else if(head==maxIndex){windowPeak=0;for(int j=0;j<K::count;++j)if(magnitudes[j]>=windowPeak){windowPeak=magnitudes[j];maxIndex=j;}}
        const double peak=windowPeak;++total;
        double g=1.;if(peak<=quietThreshold)++quiet;else {const auto c=v[K::radius];const double p=std::max(std::abs(c.l),std::abs(c.r));g=p>ceiling?ceiling/p:1.;
        // In exact arithmetic the suffix recurrence bounds 1-product(R).
        // Round the small deficit upward by a fixed double-precision margin.
        rise[K::count-1]=0.;const double* schedule=poles.data()+head+1;
        for(int j=K::count-2;j>=0;--j){const double r=schedule[j+1];rise[j]=std::min(1.,(1-r)+r*rise[j+1]+8*std::numeric_limits<double>::epsilon());}
        std::array<double,K::count> prefix{};prefix[0]=1.;for(int j=1;j<K::count;++j)prefix[j]=prefix[j-1]*schedule[j];
        std::array<double,K::count> priorUpper{};double ug=gain;
        int idx=(head+1)%K::count;
        for(int j=0;j<K::count;++j){
            ug=std::min(cap[idx],schedule[j]*ug+(1-schedule[j]));
            // Upward roundoff allowance; caps themselves are upper bounds.
            ug=std::min(1.,ug+8*std::numeric_limits<double>::epsilon());priorUpper[j]=ug;
            if(++idx==K::count)idx=0;
        }
        for(int i=1;i<4;++i){
            for(int ch=0;ch<2;++ch){
                Acc a{};std::array<double,K::count> w{};
                for(int j=0;j<K::count;++j){w[j]=h[i][j]*(ch?v[j].r:v[j].l);add(a,w[j],rise[j]);}
                double upper=safe(a.pos,a.hi,a.en),lower=safe(a.neg,-a.lo,a.ep);
                if(upper<g){upper=std::max(upper,preparedPairCap<K::count>(w,prefix,ceiling));if(upper<g)upper=std::max(upper,historyCap(w,priorUpper,upper,1));}
                if(lower<g){for(auto& z:w)z=-z;lower=std::max(lower,preparedPairCap<K::count>(w,prefix,ceiling));if(lower<g)lower=std::max(lower,historyCap(w,priorUpper,lower,1));}
                g=std::min({g,upper,lower});
            }
        }}
        if(g<1.)for(auto& q:cap)q=std::min(q,g);
        const int oldest=(head+1)%K::count;const auto y=ring[oldest];
        gain=std::min(cap[oldest],poles[oldest]*gain+(1-poles[oldest]));head=oldest;return {y.l*gain,y.r*gain};
    }
};
}
