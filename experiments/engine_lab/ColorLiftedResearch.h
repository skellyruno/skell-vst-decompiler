#pragma once
// Independent Skell color research: 2x/4x FIR oversampling of our original transfer.
// No external DSP code or vendor calibration. Fixed latency, prepare off thread.
#include "IndependentEngines.h"
#include <array>

namespace skell_lab {
template<int Factor, int BaseSpan=40, int CutoffMilli=450, int DownCutoffMilli=CutoffMilli, int Mode=1> class ColorLiftedResearch {
    static_assert(Factor==2 || Factor==4 || Factor==8,"Choose 2x, 4x or 8x");
    static_assert(Mode>=0 && Mode<=3,"0 reference, 1 direct lift, 2 difference lift, 3 paired interpolation");
    static_assert(BaseSpan>=16 && BaseSpan<=128 && BaseSpan%2==0,"Even bounded research span");
    static_assert(CutoffMilli>=400 && CutoffMilli<500,"Cutoff below base Nyquist");
    static_assert(DownCutoffMilli>=400 && DownCutoffMilli<500,"Down cutoff below base Nyquist");
public:
    static constexpr int factor=Factor, taps=BaseSpan*factor+1, history=(taps-1)/factor+1;
    static constexpr int latency=(taps-1)/factor;
private:
    static constexpr int outTaps=Mode==1?taps+factor:Mode==2?taps+factor-1:taps;
    std::array<double,outTaps> lifted{};
    double basePole=0;
    std::array<double,taps> coeff{},downCoeff{};
    std::array<double,(taps-1)/2> paired{};
    std::array<Frame,2*history> input{};
    std::array<Frame,2*outTaps> output{};
    std::array<Frame,latency> dry{};
    int inPos=0, outPos=0, dryPos=0;
    double drive=1, bias=0, mix=1, makeup=1, norm=1, dcPole=0;
    double prevIn[2]{},prevOut[2]{};
    double shape(double x,int c) noexcept {
        x=std::clamp(x,-8.0,8.0);
        const double s=std::tanh(drive*(x+bias*x*x))*norm;
        if constexpr(Mode==1)return s;
        if constexpr(Mode==2){const double y=s-prevIn[c];prevIn[c]=s;return y;}
        const double y=s-prevIn[c]+dcPole*prevOut[c];
        prevIn[c]=s;prevOut[c]=std::abs(y)<1e-30?0.0:y;
        return prevOut[c];
    }
public:
    void prepare(double sampleRate,double driveDb=12,double asymmetry=.12,double wetMix=.6,double outputDb=0) noexcept {
        const double fs=bound(sampleRate,8000,384000,48000);
        drive=fromDb(bound(driveDb,0,24,12));bias=bound(asymmetry,-.3,.3,.12);
        mix=bound(wetMix,0,1,.6);makeup=fromDb(bound(outputDb,-18,18,0));
        norm=1.0/std::max(1e-6,std::tanh(drive));dcPole=std::exp(-2*pi*5/(fs*factor));
        // Blackman-windowed sinc. Default cutoff 0.45 cycles/base-rate sample.
        const double fc=(CutoffMilli/1000.0)/factor;double sum=0;
        for(int i=0;i<taps;++i){
            const int d=i-(taps-1)/2;
            const double sinc=d?std::sin(2*pi*fc*d)/(pi*d):2*fc;
            const double w=.42-.5*std::cos(2*pi*i/(taps-1))+.08*std::cos(4*pi*i/(taps-1));
            coeff[i]=sinc*w;sum+=coeff[i];
        }
        for(auto &v:coeff)v/=sum;
        if constexpr(DownCutoffMilli!=CutoffMilli){
            const double df=(DownCutoffMilli/1000.0)/factor;double total=0;
            for(int i=0;i<taps;++i){const int d=i-(taps-1)/2;const double sinc=d?std::sin(2*pi*df*d)/(pi*d):2*df;const double w=.42-.5*std::cos(2*pi*i/(taps-1))+.08*std::cos(4*pi*i/(taps-1));downCoeff[i]=sinc*w;total+=downCoeff[i];}
            for(auto& v:downCoeff)v/=total;
        }
        for(int k=0;k<(taps-1)/2;++k){auto& c=DownCutoffMilli==CutoffMilli?coeff:downCoeff;paired[k]=.5*(c[k]+c[taps-1-k]);}
        if constexpr(Mode==1||Mode==2){
            // Lift the fixed high-rate denominator to one update per base sample.
            // Mode 2 keeps the numerator difference at the input, making constant
            // input exactly zero before convolution rather than relying on tap sums.
            basePole=std::pow(dcPole,factor);lifted.fill(0.);
            const auto& c=DownCutoffMilli==CutoffMilli?coeff:downCoeff;
            double power=1.;
            for(int j=0;j<factor;++j){
                for(int k=0;k<taps;++k){const double q=k==(taps-1)/2?c[k]:paired[std::min(k,taps-1-k)];lifted[k+j]+=q*power;if constexpr(Mode==1)lifted[k+j+1]-=q*power;}
                power*=dcPole;
            }
        }
        reset();
    }
    void reset() noexcept {input.fill({0,0});output.fill({0,0});dry.fill({0,0});inPos=outPos=dryPos=0;for(int c=0;c<2;++c)prevIn[c]=prevOut[c]=0;}
    Frame process(Frame x) noexcept {
        x={finite(x.l),finite(x.r)};
        const Frame delayed=dry[dryPos];dry[dryPos]=x; if(++dryPos==latency)dryPos=0;
        input[inPos]=input[inPos+history]=x;
        Frame wet{0,0};
        for(int phase=0;phase<factor;++phase){
            Frame up{0,0};int ix=inPos+history;
            if constexpr(Mode==3){
                if(phase==0||phase==factor/2){
                    const int n=(taps-1-phase)/factor+1;
                    for(int k=0;k<n/2;++k){const double h=.5*(coeff[phase+k*factor]+coeff[phase+(n-1-k)*factor])*factor;const auto a=input[ix-k],b=input[ix-(n-1-k)];up.l+=h*(a.l+b.l);up.r+=h*(a.r+b.r);}
                    if(n%2){const double h=coeff[phase+(n/2)*factor]*factor;up.l+=h*input[ix-n/2].l;up.r+=h*input[ix-n/2].r;}
                }else for(int k=phase;k<taps;k+=factor){const double h=coeff[k]*factor;up.l+=h*input[ix].l;up.r+=h*input[ix].r;--ix;}
            }else for(int k=phase;k<taps;k+=factor){const double h=coeff[k]*factor;up.l+=h*input[ix].l;up.r+=h*input[ix].r;--ix;}
            output[outPos]=output[outPos+outTaps]={shape(up.l,0),shape(up.r,1)};
            // Decimate at phase zero: both FIRs total exactly BaseSpan base-rate samples.
            if(phase==0){
                const int j=outPos+outTaps;
                if constexpr(Mode==1||Mode==2){
                    for(int k=0;k<outTaps;++k){wet.l+=lifted[k]*output[j-k].l;wet.r+=lifted[k]*output[j-k].r;}
                    wet.l+=basePole*prevOut[0];wet.r+=basePole*prevOut[1];
                    prevOut[0]=std::abs(wet.l)<1e-30?0.:wet.l;prevOut[1]=std::abs(wet.r)<1e-30?0.:wet.r;
                    wet={prevOut[0],prevOut[1]};
                }else{const auto& c=DownCutoffMilli==CutoffMilli?coeff:downCoeff;
                for(int k=0;k<(taps-1)/2;++k){const double h=paired[k];const auto a=output[j-k],b=output[j-(taps-1-k)];wet.l+=h*(a.l+b.l);wet.r+=h*(a.r+b.r);}
                const int mid=(taps-1)/2;wet.l+=c[mid]*output[j-mid].l;wet.r+=c[mid]*output[j-mid].r;}
            }
            if(++outPos==outTaps)outPos=0;
        }
        if(++inPos==history)inPos=0;
        return {delayed.l*(1-mix)+wet.l*mix*makeup,delayed.r*(1-mix)+wet.r*mix*makeup};
    }
};
} // namespace skell_lab
