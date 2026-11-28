#include <cmath>
// Original offline dynamics description. State resets per observation.
extern "C" int cascade_id(const double* x,double* y,unsigned n,double fs,const double* p,int stages) noexcept {
    if(!x||!y||!p||!n||n>5760000||!std::isfinite(fs)||fs<8000||fs>192000||stages<1||stages>2)return 0;
    double th[2]{},slope[2]{},attack[2]{},release[2]{},state[2]{};
    for(int j=0;j<stages;++j){
        const double* q=p+4*j;
        for(int k=0;k<4;++k)if(!std::isfinite(q[k]))return 0;
        if(q[0]<-80||q[0]>0||q[1]<0||q[1]>1||q[2]<.00005||q[2]>1||q[3]<.00005||q[3]>5)return 0;
        th[j]=std::pow(10.,q[0]/20.);slope[j]=q[1];attack[j]=std::exp(-1/(fs*q[2]));release[j]=std::exp(-1/(fs*q[3]));
    }
    for(unsigned i=0;i<n;++i){
        double v=x[i];if(!std::isfinite(v)||std::abs(v)>4)return 0;
        for(int j=0;j<stages;++j){const double a=std::abs(v),pole=a>state[j]?attack[j]:release[j];state[j]=a+pole*(state[j]-a);if(state[j]>th[j])v*=std::pow(state[j]/th[j],-slope[j]);}
        y[i]=v;
    }
    return 1;
}
