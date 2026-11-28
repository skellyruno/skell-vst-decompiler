#include <array>
#include <cassert>
#include <cmath>
#include <limits>
extern "C" int halfband_color(const double*,double*,unsigned,const double*,const double*,double,int) noexcept;
int main(){
    std::array<double,320>a{};std::array<double,32>b{};a[159]=a[160]=b[15]=b[16]=.25;
    std::array<double,8192>x{},y{},z{};x[0]=.5;
    assert(halfband_color(x.data(),y.data(),x.size(),a.data(),b.data(),4,0));assert(halfband_color(x.data(),z.data(),x.size(),a.data(),b.data(),4,1));
    for(unsigned i=0;i<x.size();++i)assert(std::abs(y[i]-z[i])<1e-14);
    unsigned max=0;for(unsigned i=0;i<y.size();++i)if(std::abs(y[i])>std::abs(y[max]))max=i;assert(max==336);
    x[0]=std::numeric_limits<double>::infinity();assert(!halfband_color(x.data(),y.data(),x.size(),a.data(),b.data(),4,1));x[0]=.1;a[0]=.1;assert(!halfband_color(x.data(),y.data(),x.size(),a.data(),b.data(),4,1));
}
