#include "StatefulStereoMod.h"
#include <new>
using Engine=skell::research::StatefulStereoMod;
extern "C" void* mod_create(double fs) noexcept {auto* e=new(std::nothrow) Engine;if(e&&!e->prepare(fs)){delete e;return nullptr;}return e;}
extern "C" void mod_destroy(void* p) noexcept {delete static_cast<Engine*>(p);}
extern "C" int mod_target(void* p,const double* a) noexcept {if(!p||!a)return 0;return static_cast<Engine*>(p)->setTarget({a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7]});}
extern "C" void mod_reset(void* p) noexcept {if(p)static_cast<Engine*>(p)->reset();}
extern "C" int mod_process(void* p,const double* x,double* y,unsigned n) noexcept {if(!p||!x||!y||!n||n>1920000)return 0;auto& e=*static_cast<Engine*>(p);for(unsigned i=0;i<n;++i){auto a=e.process(x[2*i],x[2*i+1]);y[2*i]=a[0];y[2*i+1]=a[1];}return 1;}
