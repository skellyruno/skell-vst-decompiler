#include "DelayFixture.h"
#include <cassert>
#include <iostream>

int main() {
    DelayFixture line;
    for (bool enabled:{false,true}) {
        line.reset();
        for (std::size_t i=0;i<1000;++i) {
            float l=i==7?.5f:0.f,r=i==13?-.25f:0.f;
            line.process(l,r,enabled);
            assert(l==(i==7+(enabled?DelayFixture::samples:0)?.5f:0.f));
            assert(r==(i==13+(enabled?DelayFixture::samples:0)?-.25f:0.f));
        }
    }
    float l=1.f,r=-1.f;line.process(l,r,true);line.reset();
    for(std::size_t i=0;i<1000;++i){l=r=0;line.process(l,r,true);assert(l==0&&r==0);}
    std::cout<<"SKELL_OWNED_DELAY_FIXTURE_PASS\n";
}
