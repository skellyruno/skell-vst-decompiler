#include "NativeStereoIR.h"
extern "C" int render_native(const double* h,unsigned taps,const double* in,double* out,unsigned frames) noexcept {
    try {
        std::vector<skell::research::Tap> ir(taps);
        for(unsigned i=0;i<taps;++i)for(unsigned c=0;c<4;++c)ir[i][c]=h[4*i+c];
        skell::research::NativeStereoIR e(ir);
        for(unsigned i=0;i<frames;++i){auto y=e.tick({in[2*i],in[2*i+1]});out[2*i]=y[0];out[2*i+1]=y[1];}
        return 1;
    } catch(...) { return 0; }
}
