#include "../experiments/engine_lab/ColorSplitNative.h"
#include "../experiments/engine_lab/ColorSplitMirrored.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <limits>
using namespace skell_lab;
template<int F,int S,int U,int D> unsigned check(double fs){
    std::mt19937 rng(86);std::uniform_real_distribution<double> u(-2,2);unsigned n=0;
    for(double wet:{0.,.5,1.})for(double drive:{0.,12.,24.}){
        ColorSplitNative<F,S,U,D> a;ColorSplitMirrored<F,S,U,D> b;a.prepare(fs,drive,.12,wet,0);b.prepare(fs,drive,.12,wet,0);
        for(int i=0;i<4096;++i){if(i==2049){a.reset();b.reset();}Frame x{u(rng),u(rng)};if(i==17)x.l=std::numeric_limits<double>::quiet_NaN();auto y=a.process(x),z=b.process(x);assert(y.l==z.l&&y.r==z.r);n+=2;}
    }return n;
}
int main(){unsigned n=0;for(double fs:{8000.,44100.,48000.,96000.,192000.,384000.}){n+=check<2,40,450,450>(fs);n+=check<4,40,450,450>(fs);n+=check<4,40,450,475>(fs);n+=check<4,80,450,475>(fs);}std::printf("%u exact channel comparisons at six sample rates\n",n);}
