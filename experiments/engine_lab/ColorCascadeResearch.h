#pragma once
#include "IndependentEngines.h"
#include <array>
namespace skell_lab {
// Independent two-stage 4x FIR research. Total group delay = 40 base samples.
// The second stage is a halfband with exact zero even offsets except its center.
// No allocation in process. This is NOT a bit-identical replacement.
template<int FirstTaps=65,int SecondTaps=33> class ColorCascadeResearch {
    static_assert(FirstTaps%4==1&&SecondTaps%8==1&&FirstTaps>=17&&SecondTaps>=17,"integer alignment");
    template<int N,bool Halfband> struct Stage {
        static constexpr int H=(N+1)/2;
        std::array<double,N> up{},down{};
        std::array<Frame,2*H> input{};
        std::array<Frame,2*N> output{};
        int ip=0,op=0;
        static void design(std::array<double,N>& c,double fc) noexcept {
            double sum=0;
            for(int i=0;i<N;++i){const int d=i-(N-1)/2;const double w=.42-.5*std::cos(2*pi*i/(N-1))+.08*std::cos(4*pi*i/(N-1));
                c[i]=Halfband&&d!=0&&d%2==0?0.:w*(d?std::sin(2*pi*fc*d)/(pi*d):2*fc);sum+=c[i];}
            for(auto& v:c)v/=sum;
        }
        void prepare(double u,double d)noexcept{design(up,u);design(down,d);reset();}
        void reset()noexcept{input.fill({});output.fill({});ip=op=0;}
        void push(Frame x)noexcept{input[ip]=input[ip+H]=x;}
        Frame read(int phase)const noexcept{
            Frame y{};int j=ip+H;
            for(int k=phase;k<N;k+=2,--j){if constexpr(Halfband){if((k-(N-1)/2)%2==0&&k!=(N-1)/2)continue;}const double c=2*up[k];y.l+=c*input[j].l;y.r+=c*input[j].r;}return y;
        }
        void advance()noexcept{if(++ip==H)ip=0;}
        Frame decimate(Frame x,bool sample)noexcept{
            output[op]=output[op+N]=x;Frame y{};
            if(sample){const int j=op+N;for(int k=0;k<(N-1)/2;++k){if constexpr(Halfband){if((k-(N-1)/2)%2==0)continue;}const double c=.5*(down[k]+down[N-1-k]);const auto a=output[j-k],b=output[j-(N-1-k)];y.l+=c*(a.l+b.l);y.r+=c*(a.r+b.r);}const int mid=(N-1)/2;y.l+=down[mid]*output[j-mid].l;y.r+=down[mid]*output[j-mid].r;}
            if(++op==N)op=0;
            return y;
        }
    };
    Stage<FirstTaps,false> first;Stage<SecondTaps,true> second;
public:
    static constexpr int latency=(FirstTaps-1)/2+(SecondTaps-1)/4;
private:
    static_assert(latency==40,"research fixed latency");
    std::array<Frame,latency> dry{};int pos=0;
    double drive=1,bias=0,norm=1,poleDC=0,mix=1,makeup=1,prevIn[2]{},prevOut[2]{};
    double shape(double x,int c)noexcept{x=std::clamp(x,-8.,8.);const double s=std::tanh(drive*(x+bias*x*x))*norm;const double y=s-prevIn[c]+poleDC*prevOut[c];prevIn[c]=s;prevOut[c]=std::abs(y)<1e-30?0:y;return prevOut[c];}
public:
    void prepare(double rate,double driveDb=12,double asym=.12,double wet=1,double trim=0)noexcept{
        const double fs=bound(rate,8000,384000,48000);drive=fromDb(bound(driveDb,0,24,12));bias=bound(asym,-.3,.3,.12);norm=1/std::max(1e-6,std::tanh(drive));poleDC=std::exp(-2*pi*5/(4*fs));mix=bound(wet,0,1,1);makeup=fromDb(bound(trim,-18,18,0));first.prepare(.225,.2375);second.prepare(.25,.25);reset();
    }
    void reset()noexcept{first.reset();second.reset();dry.fill({});pos=0;prevIn[0]=prevIn[1]=prevOut[0]=prevOut[1]=0;}
    Frame process(Frame x)noexcept{
        x={finite(x.l),finite(x.r)};const auto d=dry[pos];dry[pos]=x;if(++pos==latency)pos=0;first.push(x);Frame wet{};
        for(int i=0;i<2;++i){second.push(first.read(i));Frame mid{};for(int j=0;j<2;++j){const auto u=second.read(j);const auto v=second.decimate({shape(u.l,0),shape(u.r,1)},j==0);if(j==0)mid=v;}second.advance();const auto v=first.decimate(mid,i==0);if(i==0)wet=v;}
        first.advance();return {d.l*(1-mix)+wet.l*mix*makeup,d.r*(1-mix)+wet.r*mix*makeup};
    }
};
}
