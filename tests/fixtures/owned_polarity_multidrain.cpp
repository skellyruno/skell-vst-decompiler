#include "../../experiments/engine_lab/PolarityPeakResearch.h"
#include "../../experiments/engine_lab/MultiDrainResearch.h"
using namespace skell_lab;
extern "C" int polarity_render(int mode,double fs,double release,const double*x,double*y,unsigned n){
    if(!x||!y||!n||mode<0||mode>1||!std::isfinite(fs)||fs<8000||fs>384000||!std::isfinite(release)||release<1||release>1000)return 0;
    PolarityPeakGuard a;BoundedPeakGuard b;a.prepare(fs,-1,release);b.prepare(fs,-1,release,2);
    for(unsigned i=0;i<n+16;++i){Frame v=i<n?Frame{x[2*i],x[2*i+1]}:Frame{};auto z=mode?a.process(v):b.process(v);if(i>=16){y[2*(i-16)]=z.l;y[2*(i-16)+1]=z.r;}}return 1;
}
extern "C" int multibank_render(int mode,double fs,const double*x,double*y,unsigned n,unsigned interval,double* events,unsigned* stats){
    if(!x||!y||!events||!stats||!n||!interval||mode<0||mode>1||!std::isfinite(fs)||fs<8000||fs>384000)return 0;
    DrainingDelay a;MultiDrainDelay b;if(!a.prepare(fs,fs*.12+.5,1,.7,1)||!b.prepare(fs,fs*.12+.5,1,.7,1))return 0;
    double target=fs*.12+.5;unsigned count=0,accepted=0,peakBanks=1;bool pending=false;unsigned requested=0;stats[0]=stats[1]=stats[2]=stats[3]=0;
    for(unsigned i=0;i<n;++i){if(i&&i%interval==0){if(pending)events[count-1]=-1.;target=fs*(.09+.015*(count%5))+.5;requested=i;pending=true;events[count++]=-1.;}
        Frame v{x[2*i],x[2*i+1]};auto z=mode?b.process(v,target):a.process(v,target);y[2*i]=z.l;y[2*i+1]=z.r;
        if(pending&&(mode?b.activeDelay():a.activeDelay())==target){events[count-1]=1000.*(i-requested)/fs;pending=false;++accepted;}
        peakBanks=std::max(peakBanks,mode?b.liveBanks():unsigned(a.busy()?2:1));
    }stats[0]=count;stats[1]=accepted;stats[2]=mode?b.forcedRetirements():0;stats[3]=peakBanks;return 1;
}
