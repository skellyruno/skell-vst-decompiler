#include "../experiments/StatefulStereoMod.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <vector>
#include <random>
#include <cstdint>
#include <cassert>
using E=skell::research::StatefulStereoMod;
static std::uint64_t allocations=0;
void* operator new(std::size_t n){++allocations;if(auto* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
int main(){
    std::puts("rate,block,samples,callbacks,misses,peak,worst_us,total_seconds,allocations");
    for(unsigned fs:{44100u,48000u,96000u,192000u}) for(unsigned block:{64u,128u,512u,1024u}){
        E e;assert(e.prepare(fs));E::Controls p{7.4,3,.91,1.57,.35,.5,2.,.5};assert(e.setTarget(p));e.reset();
        std::vector<std::array<double,2>> input(block),output(block);std::mt19937 rng(714);std::uniform_real_distribution<double> u(-.8,.8);for(auto& x:input)x={u(rng),u(rng)};
        std::uint64_t count=0,miss=0;double worst=0.,sum=0.,peak=0.;unsigned n=10*fs;const auto before=allocations;
        for(unsigned i=0;i<n;i+=block){unsigned size=std::min(block,n-i);if(count%17==0){p.feedback=.9*std::sin(count*.13);p.cross=.5+.5*std::sin(count*.29);p.center=8+3*std::sin(count*.03);p.depth=p.center-.5;assert(e.setTarget(p));}
            auto start=std::chrono::steady_clock::now();for(unsigned j=0;j<size;++j)output[j]=e.process(input[j][0],input[j][1]);auto elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
            worst=std::max(worst,elapsed);sum+=elapsed;miss+=elapsed>double(size)/fs;++count;for(unsigned j=0;j<size;++j)for(double v:output[j]){assert(std::isfinite(v));peak=std::max(peak,std::abs(v));}
        }
        std::printf("%u,%u,%u,%llu,%llu,%.9g,%.9g,%.9g,%llu\n",fs,block,n,(unsigned long long)count,(unsigned long long)miss,peak,worst*1e6,sum,(unsigned long long)(allocations-before));assert(allocations==before);
    }
}
