#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <limits>
namespace skell_lab {
// Linear-time greedy dual cancellation for bounded 17-sample reconstruction.
// Each negative weight is pushed once, popped at most once. Fixed storage.
// Assumes finite bounded weights, 0 < poles <= 1, ceiling > 0.
template<unsigned N> double preparedPairCap(std::array<double,N> w,const std::array<double,N>& prefix,double ceiling) noexcept {
    std::array<unsigned,N> stack{};double scale=0.;
    for(double v:w)scale+=std::abs(v);
    // Keep existing conservative bound as fallback for extreme or unsupported inputs.
    if(!std::isfinite(scale)||scale>1e6||prefix[N-1]<1e-6)return 0.;
    unsigned top=0;double cost=0.,positive=0.;
    for(unsigned j=0;j<N;++j){
        if(w[j]<0.){stack[top++]=j;continue;}
        double v=w[j];
        while(v>0.&&top){
            const unsigned i=stack[top-1];const double p=prefix[j]/prefix[i];
            const double lambda=std::min(v,-w[i]/p);
            cost+=lambda*(1.-p);v-=lambda;w[i]+=lambda*p;
            // A rounded tiny positive residual must still contribute to the bound.
            if(w[i]>=0.||lambda==0.){positive+=std::max(0.,w[i]);--top;}
            else if(v==0.)break;
            else { // division rounded down: no progress is needed on this tiny residual
                --top;
            }
        }
        positive+=v;
    }
    // Allow for roundoff in prefix products, division, substitutions and sums.
    const double margin=256*std::numeric_limits<double>::epsilon()*scale;
    const double available=ceiling-cost-margin;
    return available>0.? (positive>available?available/positive:1.) : 0.;
}
}
