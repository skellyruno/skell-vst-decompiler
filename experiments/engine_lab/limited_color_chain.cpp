// Original owned research chain, raw little-endian stereo float32 I/O, no vendor code.
#include "ColorContiguous.h"
// Separate namespaces for the two pre-existing Frame definitions.
#define skell_lab skell_original_dynamics
#include "../skelliere/OriginalDynamics.h"
#undef skell_lab
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cassert>
using namespace skell_lab;
using skell_original_dynamics::LookaheadLimiter;
int main(int argc,char**argv){
    if(argc!=4&&argc!=8)return 2;
    const int fs=std::atoi(argv[2]);if(fs<8000||fs>192000)return 2;
    const double ceiling=std::atof(argv[3]);if(!std::isfinite(ceiling)||ceiling< -24||ceiling>0)return 2;
    PresenceEngine presence;ProgramLeveler leveler;ColorContiguous4x color;
    const double boost=argc==8?std::atof(argv[4]):3,ratio=argc==8?std::atof(argv[5]):4,drive=argc==8?std::atof(argv[6]):12,mix=argc==8?std::atof(argv[7]):1;
    presence.prepare(fs,2600,boost,-22,.7,1);leveler.prepare(fs,-18,ratio,4,120);
    const bool impulse=!std::strcmp(argv[1],"impulse");const bool synthetic=!std::strcmp(argv[1],"synthetic");const bool raw=!std::strcmp(argv[1],"raw");if(!impulse&&!synthetic&&!raw)return 2;
    color.prepare(fs,drive,.12,impulse?0:mix,0);LookaheadLimiter limiter(fs,ceiling,3,75);
    const unsigned latency=ColorContiguous4x::latency+limiter.latency();
    auto tick=[&](Frame in){auto p=impulse?in:presence.process(in);auto q=impulse?p:leveler.process(p);auto s=color.process(q);auto out=limiter.process({s.l,s.r});assert(std::isfinite(out[0])&&std::isfinite(out[1]));assert(std::max(std::abs(out[0]),std::abs(out[1]))<=fromDb(ceiling)+1e-12);float row[]={float(p.l),float(p.r),float(q.l),float(q.r),float(s.l),float(s.r),float(out[0]),float(out[1])};if(std::fwrite(row,sizeof(float),8,stdout)!=8)std::exit(1);};
    if(impulse){for(unsigned i=0;i<latency+16;++i)tick({i==0?.1:0,0});}
    if(synthetic){for(int i=0;i<2*fs;++i){double t=double(i)/fs;double env=(i<fs/2?.12:(i<fs?1.:(i<3*fs/2?.35:.8)));double x=env*(.48*std::sin(2*pi*110*t)+.32*std::sin(2*pi*997*t)+.22*std::sin(2*pi*11000*t));double r=env*(.46*std::sin(2*pi*127*t)+.31*std::sin(2*pi*1223*t)+.24*std::sin(2*pi*10999*t));if(i%(fs/10)==0){x+=.8;r-=.8;}tick({x,r});}}
    if(raw){float f[2];size_t n;while((n=std::fread(f,sizeof(float),2,stdin))==2)tick({f[0],f[1]});if(n!=0||std::ferror(stdin))return 2;}
    if(!impulse)for(unsigned i=0;i<latency;++i)tick({0,0});
}
