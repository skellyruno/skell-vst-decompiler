#pragma once
#include "QuietFastPolarity.h"
namespace skell_lab {
// Prepare-time policy only; no switching of gain histories during a render.
class ReleaseSelectedGuard {
    BoundedPeakGuard slow;QuietFastPolarity fast;bool useFast=false;
public:
    static constexpr int latency=ReconstructionGuard::latency;
    void prepare(double fs,double ceilingDb=-1,double releaseMs=60)noexcept {
        const double r=bound(releaseMs,1,1000,60);useFast=r<=10;
        if(useFast)fast.prepare(fs,ceilingDb,r);else slow.prepare(fs,ceilingDb,r,2);
    }
    void reset()noexcept{if(useFast)fast.reset();else slow.reset();}
    Frame process(Frame x)noexcept{return useFast?fast.process(x):slow.process(x);}
    bool polaritySelected()const noexcept{return useFast;}
};
}
