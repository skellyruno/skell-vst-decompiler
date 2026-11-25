// Original, owned DSP benchmark. Every variant has the same public ABI.
// The compiler labels are kept by the harness, never read by the recognizer.
#if defined(_WIN32)
#define API extern "C" __declspec(dllexport)
extern "C" { int _fltused=0; }
#else
#define API extern "C" __attribute__((visibility("default")))
#endif
#ifndef FAMILY
#error Choose a fixture family
#endif
#ifndef VARIANT
#define VARIANT 0
#endif
API void set_control(float* s,float x) { s[0]=x; }
API float process(float x,float* s) {
    const float p=s[0];
#if FAMILY==0
    return x*(0.25f+1.5f*p);
#elif FAMILY==1
    const float t=0.15f+0.7f*p;
#if VARIANT==0
    return x>t?t:x< -t?-t:x;
#else
    const float y=x<0?-x:x;
    const float z=y>t?t:y;
    return x<0?-z:z;
#endif
#elif FAMILY==2
    const float a=.1f+.8f*p;
#if VARIANT==0
    const float y=s[1]+a*(x-s[1]);
#else
    const float y=a*x+(1-a)*s[1];
#endif
    s[1]=y;return y;
#elif FAMILY==3
    const int n=1+int(6*p);
    int index=int(s[1]);
    const float y=s[2+((index+8-n)&7)];
    s[2+index]=x;s[1]=float((index+1)&7);return y;
#elif FAMILY==4
    const float a=x<0?-x:x;
    const float c=a>s[1]?.25f:.02f;
    s[1]+=c*(a-s[1]);
    const float t=.08f+.4f*p;
#if VARIANT==0
    return x*(s[1]>t?t/s[1]:1.f);
#else
    return x/(s[1]>t?s[1]/t:1.f);
#endif
#else
    (void)p;return x; // negative control, not included in training families
#endif
}
