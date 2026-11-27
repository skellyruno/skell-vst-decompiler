// Native-only adapter for existing independently authored lab engines.
#include "../../experiments/engine_lab/ColorOversampled.h"
using namespace skell_lab;
extern "C" int render_owned(int kind, double fs, double control, const double* in,
                            double* out, unsigned n, unsigned block) {
    if (!in || !out || !n || !block || fs<8000 || fs>384000) return 0;
    PresenceEngine presence;
    ProgramLeveler leveler;
    ColorEngine color;
    ColorOversampled2x color2;
    ColorOversampled color4;
    switch(kind) {
        case 0: presence.prepare(fs,2600,3,-22,.7,control); break;
        case 1: leveler.prepare(fs,-18,4,4,120,0,control); break;
        case 2: color.prepare(fs,12,.12,control,0); break;
        case 3: color2.prepare(fs,12,.12,control,0); break;
        case 4: color4.prepare(fs,12,.12,control,0); break;
        default:return 0;
    }
    for(unsigned pos=0;pos<n;) {
        const unsigned count=std::min(block,n-pos);
        for(unsigned i=0;i<count;++i) {
            const unsigned j=2*(pos+i);
            Frame x{in[j],in[j+1]},y;
            if(kind==0)y=presence.process(x);
            else if(kind==1)y=leveler.process(x);
            else if(kind==2)y=color.process(x);
            else if(kind==3)y=color2.process(x);
            else y=color4.process(x);
            out[j]=y.l;out[j+1]=y.r;
        }
        pos+=count;
    }
    return 1;
}
