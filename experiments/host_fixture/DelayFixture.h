#pragma once
#include <array>
#include <cstddef>

// Original owned timing fixture. Exactly 137 samples of creative delay.
class DelayFixture {
public:
    static constexpr std::size_t samples=137;
    void reset() noexcept { history={}; pos=0; }
    void process(float& left,float& right,bool enabled) noexcept {
        const float l=history[0][pos],r=history[1][pos];
        history[0][pos]=left;history[1][pos]=right;
        if (++pos==samples)pos=0;
        if (enabled){left=l;right=r;}
    }
private:
    std::array<std::array<float,samples>,2> history{};
    std::size_t pos=0;
};
