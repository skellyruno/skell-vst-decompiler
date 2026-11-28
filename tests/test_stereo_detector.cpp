#include <array>
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
extern "C" int stereo_detector(const double*,unsigned,unsigned,double,const double*,const double*,double*) noexcept;
extern "C" int stereo_detector_waveform(const double*,unsigned,double,const double*,const double*,double*) noexcept;
int main(){
    constexpr unsigned n=4800,b=240;std::array<double,n*2>x{},wave{};std::array<double,n/b*2> y{},z{};
    const double s[]{-20,4,5,150};double p[]{0,1,.16,.16,0};
    for(unsigned i=0;i<n;++i){x[2*i]=.5;x[2*i+1]=.01;}
    assert(stereo_detector(x.data(),n,b,48000,s,p,y.data()));
    assert(std::abs(y[y.size()-2]+.75*(20*std::log10(.5)+20))<1e-10);assert(y.back()==0);
    p[4]=1;assert(stereo_detector(x.data(),n,b,48000,s,p,z.data()));assert(std::abs(z.back()-z[z.size()-2])<1e-10);assert(z.back()<-10);
    p[4]=0;for(unsigned i=0;i<n;++i)std::swap(x[2*i],x[2*i+1]);assert(stereo_detector(x.data(),n,b,48000,s,p,z.data()));for(unsigned i=0;i<y.size();i+=2){assert(y[i]==z[i+1]);assert(y[i+1]==z[i]);}
    assert(stereo_detector_waveform(x.data(),n,48000,s,p,wave.data()));
    for(unsigned i=0;i<n;++i)assert(wave[2*i]==x[2*i]);
    for(unsigned i=0;i<n/b;++i){double num=0,den=0;for(unsigned j=i*b;j<(i+1)*b;++j){num+=wave[2*j+1]*x[2*j+1];den+=x[2*j+1]*x[2*j+1];}assert(std::abs(20*std::log10(num/den)-z[2*i+1])<1e-12);}
    p[0]=100;assert(!stereo_detector_waveform(x.data(),n,48000,s,p,wave.data()));p[0]=0;
    x[0]=std::numeric_limits<double>::quiet_NaN();assert(!stereo_detector(x.data(),n,b,48000,s,p,z.data()));
    assert(!stereo_detector(x.data(),n,b+1,48000,s,p,z.data()));
    std::cout<<"independent, linked, swap, convergence, invalid input passed\n";
}
