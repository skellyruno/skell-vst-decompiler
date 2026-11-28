#include <array>
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
extern "C" int topology_render(const double*,double*,unsigned,double,const double*,const double*,int,int) noexcept;
int main(){
    std::array<double,48000>x{},y{};const double s[]{-20.,4.,5.,150.},p[]{0.,1.,.159154943,.159154943};
    for(int fb:{0,1})for(int power:{0,1}){
        x.fill(0.);assert(topology_render(x.data(),y.data(),x.size(),48000,s,p,fb,power));for(auto a:y)assert(a==0.);
        x.fill(.5);assert(topology_render(x.data(),y.data(),x.size(),48000,s,p,fb,power));const double expected=.5*std::pow(5.,-.75);assert(std::abs(y.back()-expected)<1e-8);
        x[0]=std::numeric_limits<double>::quiet_NaN();assert(!topology_render(x.data(),y.data(),x.size(),48000,s,p,fb,power));
    }
    std::cout<<"Four topology hypotheses steady-state, silence and invalid input passed\n";
}
