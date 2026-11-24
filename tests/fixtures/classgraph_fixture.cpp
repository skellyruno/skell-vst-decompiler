// Owned analysis fixture: no CRT, no vendor code.
extern "C" void* typeinfo_stub[1] __asm__("??_7type_info@@6B@");
void* typeinfo_stub[1] = {nullptr};
inline void* operator new(__SIZE_TYPE__, void* p) noexcept {return p;}
struct Base { virtual double tick(double x) { return x*0.5; } };
struct Side { virtual double side(double x) { return x+1.0; } };
struct Filter : Base, Side { double z=0; double tick(double x) override { z=0.25*x+0.75*z; return z; } double side(double x) override { return x-z; } };
extern "C" __declspec(dllexport) __declspec(noinline) double fixture(double x) { Filter f; return f.tick(x)+f.side(x); }
extern "C" __declspec(dllexport) __declspec(noinline) Base* make_filter(void* buffer) { return new(buffer) Filter(); }
extern "C" int _fltused = 0;
extern "C" void entry() {}
