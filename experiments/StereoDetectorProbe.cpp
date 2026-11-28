// Original offline descriptive dynamics model. No plugin code or production integration.
#include <algorithm>
#include <cmath>
#include <cstddef>
static int run_detector(const double* x, unsigned n, unsigned block, double fs,
                               const double* settings, const double* model, double* out, double* waveform) noexcept {
    if(!x||!settings||!model||(!out&&!waveform)||!n||n>5760000||!block||block>4096||n%block||!std::isfinite(fs)||fs<8000||fs>192000)return 0;
    for(unsigned i=0;i<4;++i)if(!std::isfinite(settings[i]))return 0;
    for(unsigned i=0;i<5;++i)if(!std::isfinite(model[i]))return 0;
    if(settings[0]<-80||settings[0]>0||settings[1]<1||settings[1]>100||settings[2]<.01||settings[2]>5000||settings[3]<.01||settings[3]>5000||model[0]<-20||model[0]>20||model[1]<0||model[1]>1.1||model[2]<.001||model[2]>10||model[3]<.001||model[3]>10||model[4]<0||model[4]>1)return 0;
    const double threshold=std::pow(10.,(settings[0]+model[0])/20.);
    const double slope=(1.-1./settings[1])*model[1];
    const double attack=std::exp(-1./(fs*settings[2]*.001*model[2])),release=std::exp(-1./(fs*settings[3]*.001*model[3]));
    double state[2]{},energy[2]{},weighted[2]{};
    for(unsigned i=0;i<n;++i){
        const double l=x[2*i],r=x[2*i+1];if(!std::isfinite(l)||!std::isfinite(r)||std::max(std::abs(l),std::abs(r))>4)return 0;
        const double p[2]{std::abs(l),std::abs(r)},peak=std::max(p[0],p[1]);
        for(unsigned c=0;c<2;++c){
            const double v=p[c]+model[4]*(peak-p[c]);const double a=v>state[c]?attack:release;
            state[c]=v+a*(state[c]-v);
            const double g=state[c]>threshold?std::pow(state[c]/threshold,-slope):1.;
            if(waveform)waveform[2*i+c]=x[2*i+c]*g;
            const double w=p[c]*p[c];if(out){energy[c]+=w;weighted[c]+=w*g;}
            if(out&&(i+1)%block==0){out[2*(i/block)+c]=20*std::log10(std::max(1e-12,energy[c]>1e-15?weighted[c]/energy[c]:1.));energy[c]=weighted[c]=0.;}
        }
    }
    return 1;
}

extern "C" int stereo_detector(const double* x, unsigned n, unsigned block, double fs,
                               const double* settings, const double* model, double* out) noexcept {
    if(!out)return 0;
    return run_detector(x,n,block,fs,settings,model,out,nullptr);
}
extern "C" int stereo_detector_waveform(const double* x, unsigned n, double fs,
                                        const double* settings, const double* model, double* waveform) noexcept {
    if(!waveform)return 0;
    return run_detector(x,n,1,fs,settings,model,nullptr,waveform);
}
