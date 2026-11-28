#include <cmath>
#include <cstddef>
// Original offline phase-clock hypothesis, not production DSP.
extern "C" int phase_clock(float* delay,unsigned n,double fs,float center,float depth,float rate,int single) noexcept {
    if(!delay||!n||n>3840000||!std::isfinite(fs)||fs<8000||fs>192000||!std::isfinite(center)||!std::isfinite(depth)||!std::isfinite(rate)||center<1||center>30||depth<0||depth>10||center-depth<.1f||rate<.05f||rate>5||single<0||single>1)return 0;
    constexpr double tau=6.283185307179586476925286766559;
    const float wrap=static_cast<float>(tau),step=wrap*rate/static_cast<float>(fs);
    float phase=0.f;
    for(unsigned i=0;i<n;++i){
        if(single){delay[i]=(center-depth*std::sin(phase))*static_cast<float>(fs)/1000.f;phase+=step;if(phase>=wrap)phase-=wrap;}
        else delay[i]=static_cast<float>((static_cast<double>(center)-depth*std::sin(tau*rate*i/fs))*fs/1000.);
    }
    return 1;
}
