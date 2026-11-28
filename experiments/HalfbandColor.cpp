#include <array>
#include <cmath>
#include <cstddef>
// Original fixed-size causal halfband experiment. No JUCE/production integration.
namespace {
template<unsigned N> struct History {
    std::array<double,2*N> data{}; unsigned head=0;
    void push(double v) noexcept { head=head?head-1:N-1; data[head]=data[head+N]=v; }
    const double* samples() const noexcept {return data.data()+head;}
};
template<unsigned N,bool Symmetric> struct Halfband {
    const double* h; History<N> upHistory,evenHistory,oddHistory;
    explicit Halfband(const double* c) noexcept:h(c){}
    double side(const double* x) const noexcept {
        double sum=0;
        if constexpr(Symmetric) { for(unsigned k=0;k<N/2;++k)sum+=h[k]*(x[k]+x[N-1-k]); }
        else { for(unsigned k=0;k<N;++k)sum+=h[k]*x[k]; }
        return sum;
    }
    std::array<double,2> up(double x) noexcept {
        upHistory.push(x); const auto* p=upHistory.samples(); return {p[N/2],2*side(p)};
    }
    double down(double a,double b) noexcept {
        evenHistory.push(a); const double y=.5*evenHistory.samples()[N/2]+side(oddHistory.samples());oddHistory.push(b);return y;
    }
};
template<bool S> void run(const double* x,double* y,unsigned n,const double* h1,const double* h2,double drive) noexcept {
    Halfband<320,S> a(h1);Halfband<32,S>b(h2);
    for(unsigned i=0;i<n;++i){const auto p=a.up(x[i]);std::array<double,2> q{};
        for(unsigned j=0;j<2;++j){auto z=b.up(p[j]);q[j]=b.down(std::tanh(drive*z[0]),std::tanh(drive*z[1]));}
        y[i]=a.down(q[0],q[1]);
    }
}
}
extern "C" int halfband_color(const double* x,double* y,unsigned n,const double* h1,const double* h2,double drive,int symmetric) noexcept {
    if(!x||!y||!h1||!h2||!n||n>3840000||!std::isfinite(drive)||drive<.1||drive>20||symmetric<0||symmetric>1)return 0;
    for(unsigned i=0;i<n;++i)if(!std::isfinite(x[i])||std::abs(x[i])>4)return 0;
    for(unsigned i=0;i<320;++i)if(!std::isfinite(h1[i])||std::abs(h1[i])>1||h1[i]!=h1[319-i])return 0;
    for(unsigned i=0;i<32;++i)if(!std::isfinite(h2[i])||std::abs(h2[i])>1||h2[i]!=h2[31-i])return 0;
    if(symmetric)run<true>(x,y,n,h1,h2,drive);else run<false>(x,y,n,h1,h2,drive);return 1;
}
