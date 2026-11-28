#include <array>
#include <cassert>
#include <cmath>
#include <limits>
extern "C" int cascade_id(const double*,double*,unsigned,double,const double*,int) noexcept;
int main(){
    std::array<double,48000>x{},y{},z{},tmp{};const double p[]{-24,.75,.001,.025,-30,.5,.005,.08};
    assert(cascade_id(x.data(),y.data(),x.size(),48000,p,2));for(auto v:y)assert(v==0);
    x.fill(.8);assert(cascade_id(x.data(),y.data(),x.size(),48000,p,2));assert(cascade_id(x.data(),tmp.data(),x.size(),48000,p,1));assert(cascade_id(tmp.data(),z.data(),x.size(),48000,p+4,1));assert(y==z);
    const double a=.8*std::pow(.8/std::pow(10.,-24./20),-.75);const double b=a*std::pow(a/std::pow(10.,-30./20),-.5);assert(std::abs(y.back()-b)<1e-6);
    x[1]=std::numeric_limits<double>::quiet_NaN();assert(!cascade_id(x.data(),y.data(),x.size(),48000,p,2));assert(!cascade_id(x.data(),y.data(),x.size(),48000,p,3));
}
