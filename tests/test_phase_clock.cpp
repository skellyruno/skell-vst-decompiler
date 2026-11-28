#include <array>
#include <cassert>
#include <cmath>
#include <limits>
extern "C" int phase_clock(float*,unsigned,double,float,float,float,int) noexcept;
int main(){
    constexpr unsigned n=96000;std::array<float,n>a{},b{};
    assert(phase_clock(a.data(),n,48000,7.4f,0.f,.91f,1));for(float v:a)assert(std::abs(v-355.2f)<.001f);
    assert(phase_clock(a.data(),n,48000,7.4f,3.f,.91f,1));assert(phase_clock(b.data(),n,48000,7.4f,3.f,.91f,1));assert(a==b);
    assert(phase_clock(b.data(),n,48000,7.4f,3.f,.91f,0));assert(a!=b);
    for(float v:a)assert(v>=211.19f&&v<=499.21f);
    assert(!phase_clock(a.data(),n,48000,1.f,2.f,.91f,1));assert(!phase_clock(a.data(),0,48000,7.4f,3.f,.91f,1));assert(!phase_clock(a.data(),n,std::numeric_limits<double>::quiet_NaN(),7.4f,3.f,.91f,1));
}
