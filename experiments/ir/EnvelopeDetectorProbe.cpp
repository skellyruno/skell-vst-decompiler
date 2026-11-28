#include <algorithm>
#include <cmath>
#include <cstddef>
// Original descriptive detector-first model; not a production compressor.
// The input is finite aligned stereo. Score weighted gain over declared windows.
extern "C" void predict_detector(const double* x, unsigned n, unsigned block, double fs, const double* p, int power, double* out) noexcept {
    const double attack=std::exp(-1/(fs*p[2])),release=std::exp(-1/(fs*p[3]));
    double state=0,energy=0,weighted=0;
    for(unsigned i=0;i<n;++i){
        const double l=x[2*i],r=x[2*i+1],peak=std::max(std::abs(l),std::abs(r));
        const double value=power?peak*peak:peak;
        const double pole=value>state?attack:release;
        state=value+pole*(state-value);
        const double db=(power?10.:20.)*std::log10(std::max(state,1e-20));
        const double g=std::pow(10.,-p[1]*std::max(0.,db-p[0])/20.);
        const double w=l*l+r*r;energy+=w;weighted+=w*g;
        if((i+1)%block==0){out[i/block]=20*std::log10(std::max(1e-6,energy>1e-15?weighted/energy:1.));energy=weighted=0;}
    }
}
