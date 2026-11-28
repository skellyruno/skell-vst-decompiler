#include <cmath>
#include <algorithm>
// Original offline mono topology hypotheses. Effective slope differs in feedback;
// identical steady-state curves can therefore arise from different architectures.
extern "C" int topology_render(const double* x,double* y,unsigned n,double fs,const double* settings,const double* p,int feedback,int power) noexcept {
    if(!x||!y||!settings||!p||!n||n>1920000||!std::isfinite(fs)||fs<8000||fs>192000||feedback<0||feedback>1||power<0||power>1)return 0;
    for(int i=0;i<4;++i)if(!std::isfinite(settings[i])||!std::isfinite(p[i]))return 0;
    if(settings[1]<1||settings[1]>30||settings[2]<=0||settings[3]<=0||p[1]<=0||p[2]<=0||p[3]<=0)return 0;
    const double threshold=std::pow(10.,(settings[0]+p[0])/20.);
    const double slope=p[1]*(feedback?settings[1]-1:1-1/settings[1]);
    const double attack=std::exp(-1/(fs*.001*settings[2]*p[2])),release=std::exp(-1/(fs*.001*settings[3]*p[3]));
    double state=0,previous=0;
    for(unsigned i=0;i<n;++i){
        if(!std::isfinite(x[i])||std::abs(x[i])>4)return 0;
        double v=std::abs(feedback?previous:x[i]);if(power)v*=v;
        const double pole=v>state?attack:release;state=v+pole*(state-v);
        const double level=power?std::sqrt(state):state;
        const double g=level>threshold?std::pow(level/threshold,-slope):1.;
        previous=y[i]=x[i]*g;
        if(!std::isfinite(y[i]))return 0;
    }
    return 1;
}
