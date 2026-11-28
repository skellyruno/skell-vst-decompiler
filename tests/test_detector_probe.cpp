#include <array>
#include <cassert>
#include <cmath>
#include <iostream>
extern "C" void predict_detector(const double*,unsigned,unsigned,double,const double*,int,double*) noexcept;
int main(){
    constexpr unsigned block=240,n=4*block;std::array<double,2*n> x{};std::array<double,4> y{};
    const double p[]{-20.,.75,.001,.1};
    for(int power:{0,1}){
        predict_detector(x.data(),n,block,48000,p,power,y.data());for(auto v:y)assert(v==0);
        x.fill(.5);predict_detector(x.data(),n,block,48000,p,power,y.data());
        const double target=-.75*(20*std::log10(.5)+20);assert(y[0]>target);assert(std::abs(y.back()-target)<1e-5);assert(y[0]>y[1]);
        const double unity[]{-20.,0.,.001,.1};predict_detector(x.data(),n,block,48000,unity,power,y.data());for(auto v:y)assert(std::abs(v)<1e-12);
        x.fill(0);
    }
    std::cout<<"detector amplitude/power zero, convergence and unity checks passed\n";
}
