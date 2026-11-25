// Independent owned role-classification holdout; no vendor source or tables.
#if defined(_WIN32)
#define API extern "C" __declspec(dllexport) __declspec(noinline)
extern "C" { int _fltused=0; }
#else
#define API extern "C" __attribute__((visibility("default"),noinline))
#endif
API void gain(float* x,int n,float g) { for(int i=0;i<n;++i)x[i]*=g; }
API void filter(float* x,int n,float a,float* state) { float s=*state; for(int i=0;i<n;++i){s=a*x[i]+(1-a)*s;x[i]=s;}*state=s; }
API void curve(float* x,int n) { for(int i=0;i<n;++i){float v=x[i];x[i]=v/(1.f+v*v);} }
API void byte_copy(unsigned char* dst,const unsigned char* src,int n) { for(int i=0;i<n;++i)dst[i]=src[i]; }
API void setup(float* p,float f,float q) {p[0]=f*q;p[1]=f*f;p[2]=q*q;p[3]=1.f/(1.f+q);}
API float scalar_math(float x) {return (x*x+3.f*x)/(1.f+x*x);}
API void geometry(float* xy,int n,float scale) {for(int i=0;i<n;++i)xy[i]=xy[i]*scale+2.f;}
API float unknown(float x) {return x;}
